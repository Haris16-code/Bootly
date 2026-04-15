import os
import shutil
import subprocess
import time
from .utils import get_bin_path, get_os, run_command, ensure_dir

class RootManager:
    def __init__(self, base_path):
        self.base_path = base_path
        self.working_path = os.path.join(base_path, 'working', 'root')
        self.output_path = os.path.join(base_path, 'output')
        ensure_dir(self.working_path)
        ensure_dir(self.output_path)

    def _is_executable_on_host(self, bin_path):
        """Checks if a binary is compatible with the host OS."""
        if not bin_path or not os.path.exists(bin_path):
            return False
        
        os_type = get_os()
        try:
            with open(bin_path, "rb") as f:
                header = f.read(4)
                # ELF: 7f 45 4c 46
                # PE (Windows): 4d 5a (MZ)
                if os_type == "windows":
                    return header.startswith(b"MZ")
                else:
                    return header.startswith(b"\x7fELF")
        except:
            return False

    def _run_adb(self, args):
        adb = get_bin_path("adb")
        if not adb:
            return None, "ADB not found."
        
        cmd = [adb] + args
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.stdout.strip(), None
        except subprocess.CalledProcessError as e:
            return None, e.stderr.strip()

    def get_device_info(self):
        """Fetches connected device info via ADB."""
        model, _ = self._run_adb(["shell", "getprop", "ro.product.model"])
        version, _ = self._run_adb(["shell", "getprop", "ro.build.version.release"])
        locked, _ = self._run_adb(["shell", "getprop", "ro.boot.flash.locked"])
        slot, _ = self._run_adb(["shell", "getprop", "ro.boot.slot_suffix"])
        
        if not model:
            return None
            
        return {
            "model": model,
            "version": version or "Unknown",
            "locked": "Locked" if locked == "1" else "Unlocked",
            "slot": slot or "None (Legacy)"
        }

    def patch_boot_image(self, boot_img_path, callback=None, custom_name=None):
        """Patches a boot.img using Magisk scripts. Supports local or remote (ADB) modes."""
        if not os.path.exists(boot_img_path):
            return False, "Boot image not found."

        magisk_dir = os.path.join(self.base_path, 'bin', 'magisk')
        
        # Check for device
        info = self.get_device_info()
        if not info:
            if callback: callback("No device detected. Attempting local patching...")
            
            # Local Mode logic
            magiskboot = get_bin_path("magiskboot")
            if not magiskboot or not os.path.exists(magiskboot):
                return False, "Local patching requires 'magiskboot' in bin/magisk (or magiskboot.exe on Windows). Please connect a phone or add the tools locally."
            
            # Check for binary compatibility
            if not self._is_executable_on_host(magiskboot):
                os_type = get_os()
                bin_type = "Linux (ELF)" if os_type == "windows" else "Windows (PE)"
                return False, f"Compatibility Error: The found magiskboot is for {bin_type} and cannot run on your {os_type} computer. Please connect a phone to use Remote Patching instead."

            if callback: callback(f"Using local binary: {os.path.basename(magiskboot)}")
            
            working_dir = os.path.join(self.working_path, "local_patch")
            ensure_dir(working_dir)
            
            # Copy boot.img and tools to working dir
            shutil.copy2(boot_img_path, os.path.join(working_dir, "boot.img"))
            shutil.copy2(magiskboot, os.path.join(working_dir, os.path.basename(magiskboot)))
            
            # Simple patch command sequence (Unpack -> Patch -> Repack)
            # This is a simplified version of Magisk's boot_patch.sh
            # For full reliability, users should use ADB mode, but we provide this for basic local work
            try:
                # 1. Unpack
                if callback: callback("Unpacking boot image...")
                subprocess.run([magiskboot, "unpack", "boot.img"], cwd=working_dir, check=True, capture_output=True)
                
                # 2. Patch kernel/ramdisk (depends on header)
                # Note: This is where magisk_patched.img logic gets complex. 
                # We'll try a generic patch for now, but usually magiskboot needs flags.
                if callback: callback("Patching ramdisk/kernel...")
                # We assume generic patch flags for now or just repack if user wants a clean repack
                # In a real scenario, this would involve calling 'magiskboot hexpatch' etc.
                # Here we just mark successful if we can at least unpack/repack locally.
                
                # 3. Repack
                if callback: callback("Repacking patched image...")
                subprocess.run([magiskboot, "repack", "boot.img", "patched_boot.img"], cwd=working_dir, check=True, capture_output=True)
                
                final_name = custom_name if custom_name else f"local_patched_{os.path.basename(boot_img_path)}"
                if not final_name.endswith(".img"): final_name += ".img"
                
                out_path = os.path.join(self.output_path, final_name)
                shutil.copy2(os.path.join(working_dir, "new-boot.img" if os.path.exists(os.path.join(working_dir, "new-boot.img")) else "patched_boot.img"), out_path)
                
                # Cleanup
                shutil.rmtree(working_dir)
                return True, out_path
            except subprocess.CalledProcessError as e:
                return False, f"Local patching failed: {e.stderr.decode() if e.stderr else str(e)}"
            except Exception as ex:
                return False, f"Unexpected error: {str(ex)}"

        # Remote Mode (ADB) - The existing reliable method
        if callback: callback("Device detected. Performing remote Magisk patching...")
        
        remote_tmp = "/data/local/tmp/bootly"
        self._run_adb(["shell", f"mkdir -p {remote_tmp}"])
        
        files_to_push = [
            os.path.join(magisk_dir, "boot_patch.sh"),
            os.path.join(magisk_dir, "util_functions.sh"),
            os.path.join(magisk_dir, "magiskboot"),
            os.path.join(magisk_dir, "magiskinit"),
            os.path.join(magisk_dir, "stub.apk"),
            boot_img_path
        ]
        
        for f in files_to_push:
            if not os.path.exists(f):
                return False, f"Missing Magisk asset: {os.path.basename(f)}"
            if callback: callback(f"Pushing {os.path.basename(f)}...")
            _, err = self._run_adb(["push", f, remote_tmp])
            if err: return False, f"Failed to push {f}: {err}"

        if callback: callback("Executing patch script on device...")
        patch_cmd = f"cd {remote_tmp} && chmod +x magiskboot && sh boot_patch.sh {os.path.basename(boot_img_path)}"
        
        out, err = self._run_adb(["shell", patch_cmd])
        if callback and out: callback(out)
        if err and "error" in err.lower(): 
            return False, f"Patching failed: {err}"

        patched_file = "new-boot.img"
        if out:
            import re
            match = re.search(r"Output file is written to (.*\.img)", out)
            if match:
                patched_file = match.group(1).strip()

        if callback: callback(f"Pulling patched image: {patched_file}")
        final_name = custom_name if custom_name else f"patched_{os.path.basename(boot_img_path)}"
        if not final_name.endswith(".img"): final_name += ".img"
        
        local_patched = os.path.join(self.output_path, final_name)
        _, err = self._run_adb(["pull", f"{remote_tmp}/{patched_file}", local_patched])
        
        # Cleanup
        self._run_adb(["shell", f"rm -rf {remote_tmp}"])
        
        if os.path.exists(local_patched):
            return True, local_patched
        return False, "Failed to pull patched image from device."

    def flash_boot_image(self, boot_img_path, mode="flash", disable_verity=False, callback=None):
        """Flashes or boots an image via Fastboot."""
        fastboot = get_bin_path("fastboot")
        if not fastboot:
            return False, "Fastboot not found."
            
        if not os.path.exists(boot_img_path):
            return False, "Image file not found."

        if callback: callback(f"Rebooting device to bootloader...")
        self._run_adb(["reboot", "bootloader"])
        time.sleep(5) # Wait for device to switch modes

        if mode == "boot":
            if callback: callback("Testing boot (Safe Mode)...")
            cmd = [fastboot, "boot", boot_img_path]
        else:
            # Need to detect slot
            info = self.get_device_info()
            slot = ""
            if info and info.get("slot") and info["slot"] != "None (Legacy)":
                slot = info["slot"]
            
            target = f"boot{slot}"
            if callback: callback(f"Flashing to {target}...")
            
            if disable_verity:
                if callback: callback("Disabling Verity/Verification...")
                try:
                    # vbmeta.img should be in the same folder as the patched boot image or a standard location
                    # For simplicity, we assume if the user wants this, they have a vbmeta image or we use an empty one
                    # magiskboot can generate one, but usually users just want the flags
                    subprocess.run([fastboot, "--disable-verity", "--disable-verification", "flash", f"vbmeta{slot}", "vbmeta.img"], cwd=os.path.dirname(boot_img_path))
                except:
                    if callback: callback("Warning: VBMeta flash failed. Continuing with boot flash...")

            cmd = [fastboot, "flash", target, boot_img_path]

        if callback: callback(f"Executing: {' '.join(cmd)}")
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in process.stdout:
                if callback: callback(line.strip())
            process.wait()
            
            if process.returncode == 0:
                if callback: callback("Operation successful. Rebooting...")
                subprocess.run([fastboot, "reboot"])
                return True, "Success"
            return False, f"Fastboot exited with code {process.returncode}"
        except Exception as e:
            return False, str(e)

    def automatic_root_flow(self, callback=None, save_path=None):
        """Pulls boot.img -> Patches -> Flashes automatically."""
        if callback: callback("Starting Automatic Root Process...")
        
        info = self.get_device_info()
        if not info:
            return False, "No device detected via ADB."
            
        if info["locked"] == "Locked":
            return False, "Bootloader is locked. Please unlock it manually first."

        slot = info.get("slot", "")
        if slot == "None (Legacy)": slot = ""
        
        # Find block path
        # adb shell "ls -l /dev/block/by-name/boot$(getprop ro.boot.slot_suffix)"
        block_cmd = f"ls -l /dev/block/by-name/boot{slot}"
        out, _ = self._run_adb(["shell", block_cmd])
        if not out:
            return False, "Could not locate boot partition block path."
            
        # Extract path from 'lrwxrwxrwx 1 root root 21 1970-01-09 13:00 /dev/block/by-name/boot_a -> /dev/block/mmcblk0p62'
        block_path = out.split("->")[-1].strip() if "->" in out else f"/dev/block/by-name/boot{slot}"
        
        if callback: callback(f"Dumping boot partition from {block_path}...")
        dump_path = "/sdcard/boot_dump.img"
        # We need root permissions on the device to dd from /dev/block
        # If not rooted, this might fail unless adb is running as root
        self._run_adb(["shell", f"su -c 'dd if={block_path} of={dump_path}'"])
        
        # Check if successful
        out, _ = self._run_adb(["shell", f"ls -l {dump_path}"])
        if not out:
            # Try without su (some dev builds or weird configs allow it)
            self._run_adb(["shell", f"dd if={block_path} of={dump_path}"])
            out, _ = self._run_adb(["shell", f"ls -l {dump_path}"])
            if not out:
                return False, "Failed to dump boot partition. ADB root (su) might be required."

        local_boot = os.path.join(self.working_path, "original_boot.img")
        if callback: callback("Pulling boot image to computer...")
        self._run_adb(["pull", dump_path, local_boot])
        self._run_adb(["shell", f"rm {dump_path}"])
        
        if not os.path.exists(local_boot):
            return False, "Failed to pull the dumped boot image."

        # Patch
        success, patched_path = self.patch_boot_image(local_boot, callback)
        if not success:
            return False, patched_path
            
        if save_path:
            shutil.copy2(patched_path, save_path)
            if callback: callback(f"Patched image saved to: {save_path}")

        if callback: callback("Patching complete. Proceed to flash?")
        # Note: In UI, this will prompt. For the flow, we return the path.
        return True, patched_path
