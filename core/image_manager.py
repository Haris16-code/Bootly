import os
import shutil
import subprocess
import re
from .utils import get_bin_path, ensure_dir, clear_dir, get_os

class ImageManager:
    def __init__(self, base_path):
        self.base_path = base_path
        self.bin_path = os.path.join(base_path, 'bin')
        self.input_path = os.path.join(base_path, 'input')
        self.working_path = os.path.join(base_path, 'working')
        self.output_path = os.path.join(base_path, 'output')
        
        # Ensure directories exist
        for d in [self.input_path, self.working_path, self.output_path]:
            ensure_dir(d)

    def _get_tool_cmd(self, tool):
        """Returns a list representing the command for a tool."""
        path = get_bin_path(tool)
        if path.endswith('.py'):
            if get_os() == "windows":
                return ["python", path]
            return ["python3", path]
        return [path]

    def get_projects(self):
        """Returns a list of unpacked project folders in the base directory."""
        projects = []
        for item in os.listdir(self.base_path):
            item_path = os.path.join(self.base_path, item)
            # Exclude standard directories
            if os.path.isdir(item_path) and item not in ['input', 'output', 'working', 'bin', 'core', 'scripts', '__pycache__']:
                # A project is a folder with 'kernel', 'vendor_boot', or 'ramdisk'
                if os.path.exists(os.path.join(item_path, 'kernel')) or \
                   os.path.exists(os.path.join(item_path, 'vendor_boot')) or \
                   os.path.exists(os.path.join(item_path, 'ramdisk_compress')):
                    projects.append(item)
        return projects

    def get_raw_images(self):
        """Returns a list of raw .img files in the input directory."""
        images = []
        if os.path.exists(self.input_path):
            images = [f for f in os.listdir(self.input_path) if f.endswith('.img')]
        return images

    def unpack(self, image_name, callback=None):
        """Unpacks an Android boot/recovery image."""
        if callback: callback(f"Unpacking {image_name}...")
        
        image_path = os.path.join(self.input_path, image_name)
        folder_name = os.path.splitext(image_name)[0]
        work_folder = os.path.join(self.base_path, folder_name)
        
        # Clean work folder if it exists
        if os.path.exists(work_folder):
            shutil.rmtree(work_folder)
        os.makedirs(work_folder)

        # Run unpackbootimg
        cmd = self._get_tool_cmd('unpackbootimg') + ["-i", image_path, "-o", work_folder]
        
        if callback: callback(f"Executing: {' '.join(cmd)}")
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=self.base_path)
        
        for line in process.stdout:
            clean_line = line.strip()
            if clean_line and "carliv" not in clean_line.lower():
                if callback: callback(clean_line)
        
        process.wait()
        if process.returncode != 0:
            if callback: callback("Error: unpackbootimg failed.")
            return False

        # Ramdisk extraction
        ramdisk_files = [f for f in os.listdir(work_folder) if f.startswith('ramdisk.')]
        if not ramdisk_files:
            if callback: callback("Error: No ramdisk found.")
            return False
        
        ramdisk_file = ramdisk_files[0]
        ext = os.path.splitext(ramdisk_file)[1][1:] # gz, lzma, xz, bz2, lz4, lzo
        
        # Save compression type
        with open(os.path.join(work_folder, 'ramdisk_compress'), 'w') as f:
            f.write(ext)
        
        ramdisk_dir = os.path.join(work_folder, 'ramdisk')
        os.makedirs(ramdisk_dir)
        
        if callback: callback(f"Extracting ramdisk ({ext})...")
        
        # Decompression commands
        decompress_cmd = None
        cpio = get_bin_path("cpio")
        
        if ext == 'gz':
            tool = get_bin_path("gzip")
            decompress_cmd = f'"{tool}" -dcv "{os.path.join(work_folder, ramdisk_file)}" | "{cpio}" -i'
        elif ext == 'lzma':
            tool = get_bin_path("xz")
            decompress_cmd = f'"{tool}" -dcv --format=lzma "{os.path.join(work_folder, ramdisk_file)}" | "{cpio}" -i'
        elif ext == 'xz':
            tool = get_bin_path("xz")
            decompress_cmd = f'"{tool}" -dcv "{os.path.join(work_folder, ramdisk_file)}" | "{cpio}" -i'
        elif ext == 'bz2':
            tool = get_bin_path("bzip2")
            decompress_cmd = f'"{tool}" -dcv "{os.path.join(work_folder, ramdisk_file)}" | "{cpio}" -i'
        elif ext == 'lz4':
            tool = get_bin_path("lz4")
            decompress_cmd = f'"{tool}" -dv "{os.path.join(work_folder, ramdisk_file)}" stdout | "{cpio}" -i'
        elif ext == 'lzo':
            tool = get_bin_path("lzop")
            decompress_cmd = f'"{tool}" -dcv "{os.path.join(work_folder, ramdisk_file)}" | "{cpio}" -i'
        
        if decompress_cmd:
            process = subprocess.Popen(decompress_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=ramdisk_dir)
            for line in process.stdout:
                clean_line = line.strip()
                if clean_line and "carliv" not in clean_line.lower():
                    if callback: callback(clean_line)
            process.wait()
            
            if process.returncode == 0:
                os.remove(os.path.join(work_folder, ramdisk_file))
                if callback: callback(f"Success: Unpacked to {work_folder}")
                return True
            else:
                if callback: callback("Error: Ramdisk extraction failed.")
                return False
        else:
            if callback: callback(f"Error: Unknown compression {ext}")
            return False

    def _patch_security_flags(self, work_folder, callback=None):
        """Disables verity and AVB in ramdisk fstabs, init scripts, and props."""
        if callback: callback("Patching ramdisk security flags...")
        
        # Targets based on user "God-Tier" requirements
        targets = []
        ramdisk_dir = os.path.join(work_folder, 'ramdisk')
        if not os.path.exists(ramdisk_dir):
            return

        # Common locations for fstabs and prop files
        search_dirs = [
            ramdisk_dir,
            os.path.join(ramdisk_dir, 'vendor', 'etc'),
            os.path.join(ramdisk_dir, 'first_stage_ramdisk'),
            os.path.join(ramdisk_dir, 'etc')
        ]

        for s_dir in search_dirs:
            if not os.path.exists(s_dir): continue
            for root, dirs, files in os.walk(s_dir):
                for f in files:
                    if f.startswith('fstab.') or f.endswith('.rc') or f.endswith('.prop') or f in ['build.prop', 'default.prop', 'recovery.fstab']:
                        targets.append(os.path.join(root, f))
        
        # Also look for .dts files in the whole work folder
        for root, dirs, files in os.walk(work_folder):
            for f in files:
                if f.endswith('.dts'):
                    targets.append(os.path.join(root, f))

        # "Refined Security Sauce" Patterns
        patterns = [
            (re.compile(r",?verify\b"), ""),                # dm-verity
            (re.compile(r",?avb(?:=[^, ]*)?"), ""),         # AVB Flags
            (re.compile(r",?support_scsi_logging\b"), ""),   # Verification logging
            (re.compile(r"^ro\.config\.dmverity=.*$", re.M), "ro.config.dmverity=false") # Prop Logic
        ]

        modified_count = 0
        for target in targets:
            try:
                with open(target, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                new_content = content
                for pattern, repl in patterns:
                    new_content = pattern.sub(repl, new_content)

                if new_content != content:
                    # Professional Cleanup Phase
                    lines = []
                    for line in new_content.splitlines():
                        # Refined clean order
                        line = line.replace(",,", ",")  # Remove double commas
                        line = line.replace(" ,", " ")  # Remove leading space-comma
                        line = line.strip(",")          # Remove leading/trailing commas
                        lines.append(line.rstrip())
                    
                    with open(target, 'w', encoding='utf-8', newline='\n') as f:
                        f.write("\n".join(lines) + "\n")
                    modified_count += 1
            except Exception as e:
                if callback: callback(f"Warning: Could not patch {os.path.basename(target)}: {str(e)}")

        if callback: callback(f"Security patching complete. Modified {modified_count} files.")

    def repack(self, folder_name, callback=None, patch_vbmeta=False, custom_name=None):
        """Repacks a work folder into an Android boot/recovery image."""
        if callback: callback(f"Repacking {folder_name}...")
        
        work_folder = os.path.join(self.base_path, folder_name)
        if not os.path.exists(work_folder):
            if callback: callback(f"Error: Folder {folder_name} not found.")
            return False
            
        # Check kernel/ramdisk
        if not os.path.exists(os.path.join(work_folder, 'kernel')) and not os.path.exists(os.path.join(work_folder, 'vendor_boot')):
             if callback: callback("Error: Kernel or vendor_boot folder missing.")
             return False
             
        # Compress ramdisk
        compress_file = os.path.join(work_folder, 'ramdisk_compress')
        if not os.path.exists(compress_file):
            if callback: callback("Error: ramdisk_compress file missing.")
            return False
            
        with open(compress_file, 'r') as f:
            compress = f.read().strip()
            
        ramdisk_out = os.path.join(work_folder, f"ramdisk.{compress}")
        ramdisk_dir = os.path.join(work_folder, 'ramdisk')
        
        if callback: callback(f"Compressing ramdisk ({compress})...")
        
        compress_cmd = None
        mkbootfs = get_bin_path("mkbootfs")
        minigzip = get_bin_path("minigzip") # Use gzip if minigzip not found on Linux/Mac
        if get_os() != "windows" and minigzip == "minigzip":
             minigzip = "gzip"
        xz = get_bin_path("xz")
        bzip2 = get_bin_path("bzip2")
        lz4 = get_bin_path("lz4")
        lzop = get_bin_path("lzop")

        if compress == 'gz':
            compress_cmd = f'"{mkbootfs}" ramdisk | "{minigzip}" -c -9 > ramdisk.gz'
        elif compress == 'xz':
            compress_cmd = f'"{mkbootfs}" ramdisk | "{xz}" -1zv -Ccrc32 > ramdisk.xz'
        elif compress == 'lzma':
            compress_cmd = f'"{mkbootfs}" ramdisk | "{xz}" --format=lzma -1zv > ramdisk.lzma'
        elif compress == 'bz2':
            compress_cmd = f'"{mkbootfs}" ramdisk | "{bzip2}" -zv > ramdisk.bz2'
        elif compress == 'lz4':
            compress_cmd = f'"{mkbootfs}" ramdisk | "{lz4}" -l -12 --favor-decSpeed stdin stdout > ramdisk.lz4'
        elif compress == 'lzo':
            compress_cmd = f'"{mkbootfs}" ramdisk | "{lzop}" -v > ramdisk.lzo'

        if compress_cmd:
            process = subprocess.Popen(compress_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=work_folder)
            for line in process.stdout:
                clean_line = line.strip()
                if clean_line and "carliv" not in clean_line.lower():
                    if callback: callback(clean_line)
            process.wait()
            if process.returncode != 0:
                if callback: callback("Error: Ramdisk compression failed.")
                return False
        
        # Build mkbootimg command
        args = []
        
        # Helper to read file and add argument
        def add_arg(filename, arg_name, wrapper=""):
            p = os.path.join(work_folder, filename)
            if os.path.exists(p):
                with open(p, 'r') as f:
                    val = f.read().strip()
                    if val:
                        args.append(arg_name)
                        args.append(f"{wrapper}{val}{wrapper}")

        is_vendor = os.path.exists(os.path.join(work_folder, 'vendor_boot'))
        
        if is_vendor:
            args.extend(["--vendor_ramdisk", os.path.join(work_folder, f"ramdisk.{compress}")])
            add_arg("vendor_cmdline", "--vendor_cmdline", "")
        else:
            args.extend(["--kernel", os.path.join(work_folder, "kernel")])
            args.extend(["--ramdisk", os.path.join(work_folder, f"ramdisk.{compress}")])
            add_arg("cmdline", "--cmdline", "")

        add_arg("board", "--board", "")
        add_arg("base", "--base")
        add_arg("pagesize", "--pagesize")
        add_arg("kernel_offset", "--kernel_offset")
        add_arg("ramdisk_offset", "--ramdisk_offset")
        add_arg("second_offset", "--second_offset")
        add_arg("tags_offset", "--tags_offset")
        add_arg("os_version", "--os_version")
        add_arg("os_patch_level", "--os_patch_level")
        add_arg("header_version", "--header_version")
        add_arg("hashtype", "--hashtype")
        
        # files
        if os.path.exists(os.path.join(work_folder, "second")):
            args.extend(["--second", os.path.join(work_folder, "second")])
        if os.path.exists(os.path.join(work_folder, "dt")):
            args.extend(["--dt", os.path.join(work_folder, "dt")])
        if os.path.exists(os.path.join(work_folder, "dtb")):
            args.extend(["--dtb", os.path.join(work_folder, "dtb")])
        add_arg("dtb_offset", "--dtb_offset")
        if os.path.exists(os.path.join(work_folder, "recovery_dtbo")):
            args.extend(["--recovery_dtbo", os.path.join(work_folder, "recovery_dtbo")])
        if os.path.exists(os.path.join(work_folder, "recovery_acpio")):
            args.extend(["--recovery_acpio", os.path.join(work_folder, "recovery_acpio")])
            
        # MTK
        if os.path.exists(os.path.join(work_folder, "mtk")):
             with open(os.path.join(work_folder, "mtk"), 'r') as f:
                 mtk_val = f.read().strip()
                 args.extend(["--mtk", mtk_val])

        # Output
        new_image_name = custom_name if custom_name else f"{folder_name}-repacked.img"
        output_image = os.path.join(self.output_path, new_image_name)
        
        if is_vendor:
            args.extend(["--vendor_boot", output_image])
        else:
            args.extend(["--output", output_image])

        mkbootimg_cmd = self._get_tool_cmd('mkbootimg')
        final_cmd = mkbootimg_cmd + args
        
        if callback: callback(f"Executing: {' '.join(final_cmd)}")
        
        process = subprocess.Popen(final_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=self.base_path)
        for line in process.stdout:
            clean_line = line.strip()
            if clean_line and "carliv" not in clean_line.lower():
                if callback: callback(clean_line)
        process.wait()
        
        if process.returncode == 0:
            if callback: callback(f"Success! Repacked image: {output_image}")
            
            # --- VBMeta Chain Patching Logic ---
            if patch_vbmeta:
                if callback: callback("Scanning for VBMeta images to patch...")
                vbmeta_found = []
                for f in os.listdir(work_folder):
                    if f.startswith("vbmeta") and f.endswith(".img"):
                        vbmeta_found.append(f)
                
                avbtool_cmd_base = self._get_tool_cmd('avbtool')
                
                if vbmeta_found:
                    for vb in vbmeta_found:
                        src_path = os.path.join(work_folder, vb)
                        out_name = f"{os.path.splitext(vb)[0]}_patched.img"
                        dst_path = os.path.join(self.output_path, out_name)
                        
                        # Command for existing image: patch_vbmeta
                        cmd = avbtool_cmd_base + ["patch_vbmeta", "--image", src_path, "--flags", "3"]
                        if callback: callback(f"Patching Chain: {vb} -> {out_name}")
                        
                        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=self.base_path)
                        for line in proc.stdout:
                            if callback: callback(line.strip())
                        proc.wait()
                        
                        # Since patch_vbmeta modifies in-place, we should copy it to output
                        shutil.copy2(src_path, dst_path)
                else:
                    # Empty Bypass Fallback
                    if callback: callback("No VBMeta found in project. Generating standalone bypass...")
                    out_name = "vbmeta_patched.img"
                    dst_path = os.path.join(self.output_path, out_name)
                    
                    # Command for new image: make_vbmeta_image
                    cmd = avbtool_cmd_base + ["make_vbmeta_image", "--flags", "3", "--padding_size", "4096", "--output", dst_path]
                    
                    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=self.base_path)
                    for line in proc.stdout:
                        if callback: callback(line.strip())
                    proc.wait()
                    if proc.returncode == 0:
                        if callback: callback(f"Generated Empty Bypass: {out_name}")

            # Clean up temporary ramdisk
            os.remove(os.path.join(work_folder, f"ramdisk.{compress}"))
            return True
        else:
            if callback: callback("Error: mkbootimg failed.")
            return False

    def get_info(self, image_name):
        """Gets information about an image."""
        image_path = os.path.join(self.input_path, image_name)
        if not os.path.exists(image_path):
             image_path = os.path.join(self.working_path, image_name)
             if not os.path.exists(image_path):
                 return "Error: Image not found."

        cmd = self._get_tool_cmd('unpackbootimg') + ["-i", image_path, "--info"]
        try:
            result = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
            # Filter output
            filtered = [line for line in result.split('\n') if "carliv" not in line.lower() and line.strip()]
            return '\n'.join(filtered)
        except subprocess.CalledProcessError as e:
            return e.output

    def generate_empty_vbmeta(self, filename, callback=None):
        """Generates a standalone disabled VBMeta image."""
        if callback: callback(f"Generating empty bypass VBMeta: {filename}")
        
        dst_path = os.path.join(self.output_path, filename)
        avbtool_cmd_base = self._get_tool_cmd('avbtool')
        
        # Command: make_vbmeta_image --flags 3 --padding_size 4096 --output [path]
        cmd = avbtool_cmd_base + ["make_vbmeta_image", "--flags", "3", "--padding_size", "4096", "--output", dst_path]
        
        if callback: callback(f"Executing: {' '.join(cmd)}")
        
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=self.base_path)
            for line in process.stdout:
                if callback: callback(line.strip())
            process.wait()
            
            if process.returncode == 0:
                if callback: callback(f"Success! VBMeta generated: {dst_path}")
                return True
            else:
                if callback: callback("Error: avbtool make_vbmeta_image failed.")
                return False
        except Exception as e:
            if callback: callback(f"Error: {str(e)}")
            return False

    def clear(self, type="all"):
        """Clears working or output directories."""
        if type == "all":
            # Only clear image-related things, keep original folders
            for item in os.listdir(self.base_path):
                if os.path.isdir(os.path.join(self.base_path, item)):
                    # Check if it's an unpacked image folder (contains kernel or ramdisk)
                    if os.path.exists(os.path.join(self.base_path, item, 'kernel')) or \
                       os.path.exists(os.path.join(self.base_path, item, 'ramdisk_compress')):
                        shutil.rmtree(os.path.join(self.base_path, item))
            clear_dir(self.working_path)
        elif type == "output":
            clear_dir(self.output_path)

    def avb_info_image(self, image_path, callback=None):
        """Wrapper for avbtool info_image."""
        cmd = self._get_tool_cmd('avbtool') + ["info_image", "--image", image_path]
        try:
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
            return output
        except subprocess.CalledProcessError as e:
            return f"Error: {e.output}"

    def avb_verify_image(self, image_path, key_path=None, callback=None):
        """Wrapper for avbtool verify_image."""
        cmd = self._get_tool_cmd('avbtool') + ["verify_image", "--image", image_path]
        if key_path:
            cmd.extend(["--key", key_path])
        
        if callback: callback(f"Verifying: {image_path}...")
        try:
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
            if callback: callback(output)
            return True
        except subprocess.CalledProcessError as e:
            if callback: callback(f"Verification Failed:\n{e.output}")
            return False

    def avb_add_hash_footer(self, image_path, partition_name, partition_size, algorithm="NONE", key_path=None, callback=None):
        """Wrapper for avbtool add_hash_footer."""
        cmd = self._get_tool_cmd('avbtool') + [
            "add_hash_footer", 
            "--image", image_path,
            "--partition_name", partition_name,
            "--partition_size", str(partition_size),
            "--algorithm", algorithm,
            "--salt", os.urandom(32).hex()
        ]
        if key_path:
            cmd.extend(["--key", key_path])
        
        if callback: callback(f"Adding hash footer to {partition_name}...")
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in process.stdout:
                if callback: callback(line.strip())
            process.wait()
            return process.returncode == 0
        except Exception as e:
            if callback: callback(f"Error: {str(e)}")
            return False

    def avb_patch_vbmeta(self, image_path, rollback_index=None, key_path=None, algorithm=None, flags=None, callback=None):
        """Generic VBMeta patching tool (keys, rollback, flags)."""
        cmd = self._get_tool_cmd('avbtool') + ["patch_vbmeta", "--image", image_path]
        
        if rollback_index is not None:
            cmd.extend(["--rollback_index", str(rollback_index)])
        if key_path:
            cmd.extend(["--key", key_path])
        if algorithm:
            cmd.extend(["--algorithm", algorithm])
        if flags is not None:
            cmd.extend(["--flags", str(flags)])
            
        if callback: callback(f"Patching VBMeta: {image_path}...")
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in process.stdout:
                if callback: callback(line.strip())
            process.wait()
            return process.returncode == 0
        except Exception as e:
            if callback: callback(f"Error: {str(e)}")
            return False

    def avb_calculate_size(self, image_path, partition_size, callback=None):
        """Uses --calc_max_image_size to determine the maximum size for an image."""
        cmd = self._get_tool_cmd('avbtool') + [
            "add_hash_footer",
            "--image", image_path,
            "--partition_size", str(partition_size),
            "--calc_max_image_size"
        ]
        try:
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
            return output.strip()
        except subprocess.CalledProcessError as e:
            return f"Error: {e.output}"
