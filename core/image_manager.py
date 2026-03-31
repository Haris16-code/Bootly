import os
import shutil
import subprocess
from .utils import get_bin_path, ensure_dir, clear_dir

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
        unpackbootimg = os.path.join(self.bin_path, 'unpackbootimg.exe')
        cmd = [unpackbootimg, "-i", image_path, "-o", work_folder]
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
        if ext == 'gz':
            decompress_cmd = f'"{os.path.join(self.bin_path, "gzip.exe")}" -dcv "{os.path.join(work_folder, ramdisk_file)}" | "{os.path.join(self.bin_path, "cpio.exe")}" -i'
        elif ext == 'lzma':
            decompress_cmd = f'"{os.path.join(self.bin_path, "xz.exe")}" -dcv --format=lzma "{os.path.join(work_folder, ramdisk_file)}" | "{os.path.join(self.bin_path, "cpio.exe")}" -i'
        elif ext == 'xz':
            decompress_cmd = f'"{os.path.join(self.bin_path, "xz.exe")}" -dcv "{os.path.join(work_folder, ramdisk_file)}" | "{os.path.join(self.bin_path, "cpio.exe")}" -i'
        elif ext == 'bz2':
            decompress_cmd = f'"{os.path.join(self.bin_path, "bzip2.exe")}" -dcv "{os.path.join(work_folder, ramdisk_file)}" | "{os.path.join(self.bin_path, "cpio.exe")}" -i'
        elif ext == 'lz4':
            decompress_cmd = f'"{os.path.join(self.bin_path, "lz4.exe")}" -dv "{os.path.join(work_folder, ramdisk_file)}" stdout | "{os.path.join(self.bin_path, "cpio.exe")}" -i'
        elif ext == 'lzo':
            decompress_cmd = f'"{os.path.join(self.bin_path, "lzop.exe")}" -dcv "{os.path.join(work_folder, ramdisk_file)}" | "{os.path.join(self.bin_path, "cpio.exe")}" -i'
        
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

    def repack(self, folder_name, callback=None):
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
        if compress == 'gz':
            compress_cmd = f'"{os.path.join(self.bin_path, "mkbootfs.exe")}" ramdisk | "{os.path.join(self.bin_path, "minigzip.exe")}" -c -9 > ramdisk.gz'
        elif compress == 'xz':
            compress_cmd = f'"{os.path.join(self.bin_path, "mkbootfs.exe")}" ramdisk | "{os.path.join(self.bin_path, "xz.exe")}" -1zv -Ccrc32 > ramdisk.xz'
        elif compress == 'lzma':
            compress_cmd = f'"{os.path.join(self.bin_path, "mkbootfs.exe")}" ramdisk | "{os.path.join(self.bin_path, "xz.exe")}" --format=lzma -1zv > ramdisk.lzma'
        elif compress == 'bz2':
            compress_cmd = f'"{os.path.join(self.bin_path, "mkbootfs.exe")}" ramdisk | "{os.path.join(self.bin_path, "bzip2.exe")}" -zv > ramdisk.bz2'
        elif compress == 'lz4':
            compress_cmd = f'"{os.path.join(self.bin_path, "mkbootfs.exe")}" ramdisk | "{os.path.join(self.bin_path, "lz4.exe")}" -l stdin stdout > ramdisk.lz4'
        elif compress == 'lzo':
            compress_cmd = f'"{os.path.join(self.bin_path, "mkbootfs.exe")}" ramdisk | "{os.path.join(self.bin_path, "lzop.exe")}" -v > ramdisk.lzo'

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
        new_image_name = f"{folder_name}-repacked.img"
        output_image = os.path.join(self.output_path, new_image_name)
        
        if is_vendor:
            args.extend(["--vendor_boot", output_image])
        else:
            args.extend(["--output", output_image])

        mkbootimg = os.path.join(self.bin_path, 'mkbootimg.exe')
        final_cmd = [mkbootimg] + args
        
        if callback: callback(f"Executing: {' '.join(final_cmd)}")
        
        process = subprocess.Popen(final_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=self.base_path)
        for line in process.stdout:
            clean_line = line.strip()
            if clean_line and "carliv" not in clean_line.lower():
                if callback: callback(clean_line)
        process.wait()
        
        if process.returncode == 0:
            if callback: callback(f"Success! Repacked image: {output_image}")
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

        unpackbootimg = os.path.join(self.bin_path, 'unpackbootimg.exe')
        cmd = [unpackbootimg, "-i", image_path, "--info"]
        try:
            result = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
            # Filter output
            filtered = [line for line in result.split('\n') if "carliv" not in line.lower() and line.strip()]
            return '\n'.join(filtered)
        except subprocess.CalledProcessError as e:
            return e.output

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
