#!/usr/bin/env python3

import os
import subprocess
import sys
import wx
import datetime
import json
import logging
import threading
import zipfile
import tarfile
import zlib
import subprocess

# Configure logging
log_file = "pdf_converter.log"
logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def check_program_exists(program):
    try:
        if program == "/usr/bin/qpdf":
            subprocess.run([program, "--help"], capture_output=True, check=True, text=True)
            return True
        else:
            subprocess.run([program, "-v"], capture_output=True, check=True, text=True)
            return True
    except FileNotFoundError:
        return False
    except subprocess.CalledProcessError as e:
        logging.error(f"Error checking '{program}': {e.stderr}")
        wx.MessageBox(f"Error checking '{program}': {e.stderr}", "Error", wx.OK | wx.ICON_ERROR)
        return False

def find_pdfs_recursive(directory):
    pdf_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith((".pdf", ".PDF")):
                pdf_files.append(os.path.join(root, file))
    return pdf_files

def convert_pdfs_to_text(pdf_dir, output_dir, pdftotext_path, output_text):
    try:
        pdf_files = find_pdfs_recursive(pdf_dir)
        if not pdf_files:
            wx.MessageBox("No PDF files found in the specified directory or its subdirectories.", "Info", wx.OK | wx.ICON_INFORMATION)
            return

        total_files = len(pdf_files)
        for i, pdf_file in enumerate(pdf_files):
            relative_path = os.path.relpath(pdf_file, pdf_dir)
            output_path = os.path.join(output_dir, relative_path)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            txt_path = os.path.join(output_path[:-4] + ".txt")

            try:
                process = subprocess.Popen(
                    [pdftotext_path, "-layout", "-nopgbrk", "-enc", "UTF-8", pdf_file, txt_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                stdout, stderr = process.communicate()
                wx.CallAfter(output_text.AppendText, stdout)
                if stderr:
                    wx.CallAfter(output_text.AppendText, f"\n[Error]: {stderr.strip()}")

            except FileNotFoundError:
                wx.MessageBox(f"Error: Input PDF file '{pdf_file}' not found!", "Error", wx.OK | wx.ICON_ERROR)
            except subprocess.CalledProcessError as e:
                wx.MessageBox(f"Error converting PDF '{pdf_file}': {e.stderr}", "Error", wx.OK | wx.ICON_ERROR)
            except Exception as e:
                wx.MessageBox(f"An unexpected error occurred during conversion of '{pdf_file}': {e}", "Error", wx.OK | wx.ICON_ERROR)

    except Exception as e:
        wx.MessageBox(f"An unexpected error occurred: {e}", "Error", wx.OK | wx.ICON_ERROR)


def compress_pdf(pdf_path, compressed_path, quality="ebook", gs_path="/usr/bin/gs", gs_flags=None):
    try:
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        gs_command = [gs_path, "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.4",
                      f"-dPDFSETTINGS=/{quality}", "-dNOPAUSE", "-dQUIET", "-dBATCH",
                      "-sOutputFile=" + compressed_path, pdf_path]
        gs_command.extend(gs_flags or [])
        subprocess.run(gs_command, check=True, stderr=subprocess.PIPE, text=True)
        return True
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return False
    except subprocess.CalledProcessError as e:
        print(f"Error compressing PDF '{pdf_path}': {e.stderr}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during compression of '{pdf_path}': {e}")
        return False

def decompress_pdf(pdf_path, decompressed_path, qpdf_path="/usr/bin/qpdf"):
    try:
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        subprocess.run([qpdf_path, "--linearize", pdf_path, decompressed_path], check=True)
        return True
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return False
    except subprocess.CalledProcessError as e:
        print(f"Error decompressing PDF: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during decompression: {pdf_path}: {e}")
        return False

def get_folder_size(folder_path):
    total_size = 0
    for dirpath, _, filenames in os.walk(folder_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            # skip if it is symbolic link
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    return total_size

def format_bytes(size):
    power = 2**10
    n = 0
    units = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power and n < len(units) -1:
        size /= power
        n += 1
    return f"{size:.2f} {units[n]}B"

def compress_folder(folder_path, output_filename, compression_type="zip"):
    try:
        if compression_type == "zip":
            with zipfile.ZipFile(output_filename, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for root, _, files in os.walk(folder_path):
                    for file in files:
                        zf.write(os.path.join(root, file), arcname=os.path.relpath(os.path.join(root, file), folder_path))
        elif compression_type == "7z":
            # 7z compression requires an external command.
            # This example uses a 7z command; adjust based on your 7z installation.
            command = ["7z", "a", "-t7z", output_filename, folder_path]
            subprocess.run(command, check=True)

        elif compression_type == "tar.gz":
            with tarfile.open(output_filename, "w:gz") as tar:
                for root, _, files in os.walk(folder_path):
                    for file in files:
                        tar.add(os.path.join(root, file), arcname=os.path.relpath(os.path.join(root, file), folder_path))
        else:
            raise ValueError(f"Unsupported compression type: {compression_type}")
        return True
    except (FileNotFoundError, subprocess.CalledProcessError, ValueError, OSError) as e:
        logging.error(f"Error compressing folder '{folder_path}': {e}")
        wx.MessageBox(f"Error compressing folder: {e}", "Error", wx.OK | wx.ICON_ERROR)
        return False

class PDFConverterGUI(wx.Frame):
    def __init__(self, parent, title="PDF Workshop"):
        super(PDFConverterGUI, self).__init__(parent, title=title, size=(600, 650), style=wx.DEFAULT_FRAME_STYLE & ~wx.RESIZE_BORDER)

        # Check for required programs
        if not check_program_exists("pdftotext"):
            wx.MessageBox("Error: pdftotext not found. Please install poppler-utils.", "Error", wx.OK | wx.ICON_ERROR)
            self.Close()
            return

        if not check_program_exists("/usr/bin/gs"):
            wx.MessageBox("Error: Ghostscript not found. Please install Ghostscript.", "Error", wx.OK | wx.ICON_ERROR)
            self.Close()
            return

        if not check_program_exists("/usr/bin/qpdf"):
            wx.MessageBox("Error: qpdf not found. Please install qpdf.", "Error", wx.OK | wx.ICON_ERROR)
            self.Close()
            return



        self.panel = wx.Panel(self)
        self.sizer = wx.BoxSizer(wx.VERTICAL)

        # Load settings from config file
        self.settings = self.load_settings("config.json")

        # Color scheme
        self.background_color = wx.Colour(240, 240, 240)
        self.accent_color = wx.Colour(50, 150, 200)

        # Input/output fields
        input_dir_label = wx.StaticText(self.panel, label="Input Directory:")
        self.input_dir_edit = wx.TextCtrl(self.panel, value=self.settings.get("input_dir", "."))
        output_dir_label = wx.StaticText(self.panel, label="Output Directory:")
        self.output_dir_edit = wx.TextCtrl(self.panel, value=self.settings.get("output_dir", "."))
        pdftotext_path_label = wx.StaticText(self.panel, label="pdftotext Path:")
        self.pdftotext_path_edit = wx.TextCtrl(self.panel, value=self.settings.get("pdftotext_path", "/usr/bin/pdftotext"))

        self.input_dir_edit.SetBackgroundColour(self.background_color)
        self.output_dir_edit.SetBackgroundColour(self.background_color)
        self.pdftotext_path_edit.SetBackgroundColour(self.background_color)

        # Compress/Decompress Options
        self.action_label = wx.StaticText(self.panel, label="Action:")
        self.action_combo = wx.ComboBox(self.panel, choices=["Convert to Text", "Compress PDF", "Decompress PDF"], style=wx.CB_READONLY)

        self.compression_options = {
            "screen": "Screen (lowest)",
            "ebook": "eBook",
            "prepress": "Prepress",
            "default": "Default"
        }

        self.quality_group = wx.StaticBoxSizer(wx.VERTICAL, self.panel, "Compression Quality")
        self.quality_radio_buttons = {}
        first_radio = True
        for quality, description in self.compression_options.items():
            style = wx.RB_GROUP if first_radio else 0
            radio_button = wx.RadioButton(self.panel, label=description, style=style)
            first_radio = False
            radio_button.quality = quality
            self.quality_group.Add(radio_button, 0, wx.ALL, 5)
            radio_button.Bind(wx.EVT_RADIOBUTTON, self.on_quality_selected)
            self.quality_radio_buttons[quality] = radio_button

        self.quality_group.Show(False)
        self.selected_quality = self.settings.get("compression_quality", "ebook")

        # Ghostscript flags
        self.gs_flags_box = wx.StaticBoxSizer(wx.VERTICAL, self.panel, "Ghostscript Flags")
        self.safer_checkbox = wx.CheckBox(self.panel, label="Safer Mode (-dSAFER)")
        self.gs_flags_box.Add(self.safer_checkbox, 0, wx.ALL, 5)
        self.verbose_checkbox = wx.CheckBox(self.panel, label="Verbose Mode (-v)")
        self.gs_flags_box.Add(self.verbose_checkbox, 0, wx.ALL, 5)

        # Buttons
        self.browse_input_button = wx.Button(self.panel, label="Browse Input")
        self.browse_output_button = wx.Button(self.panel, label="Browse Output")
        self.convert_button = wx.Button(self.panel, label="Convert/Compress/Decompress")
        #self.progress_bar = wx.Gauge(self.panel, range=100, style=wx.GA_HORIZONTAL)
        #self.progress_bar.Hide()

        self.browse_input_button.SetBackgroundColour(self.accent_color)
        self.browse_output_button.SetBackgroundColour(self.accent_color)
        self.convert_button.SetBackgroundColour(self.accent_color)
        self.browse_input_button.SetForegroundColour(wx.WHITE)
        self.browse_output_button.SetForegroundColour(wx.WHITE)
        self.convert_button.SetForegroundColour(wx.WHITE)

        # Compression type chooser
        self.compression_type_label = wx.StaticText(self.panel, label="Compression Type:")
        self.compression_type_combo = wx.ComboBox(self.panel, choices=["zip", "7z", "tar.gz", "none"], style=wx.CB_READONLY)
        self.compression_type_combo.SetValue("zip")

        # Text control for terminal output
        self.output_text = wx.TextCtrl(self.panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2)
        self.output_text.SetBackgroundColour(wx.Colour(220, 220, 220))
        self.output_text.SetFont(wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))


        # Layout
        sizer = wx.GridBagSizer(5, 5)
        sizer.Add(input_dir_label, pos=(0, 0), flag=wx.ALL, border=5)
        sizer.Add(self.input_dir_edit, pos=(0, 1), flag=wx.EXPAND | wx.ALL, border=5)
        sizer.Add(self.browse_input_button, pos=(0, 2), flag=wx.ALL, border=5)
        sizer.Add(output_dir_label, pos=(1, 0), flag=wx.ALL, border=5)
        sizer.Add(self.output_dir_edit, pos=(1, 1), flag=wx.EXPAND | wx.ALL, border=5)
        sizer.Add(self.browse_output_button, pos=(1, 2), flag=wx.ALL, border=5)
        sizer.Add(pdftotext_path_label, pos=(2, 0), flag=wx.ALL, border=5)
        sizer.Add(self.pdftotext_path_edit, pos=(2, 1), flag=wx.EXPAND | wx.ALL, border=5)
        sizer.Add(self.action_label, pos=(3, 0), flag=wx.ALL, border=5)
        sizer.Add(self.action_combo, pos=(3, 1), flag=wx.EXPAND | wx.ALL, border=5)
        sizer.Add(self.quality_group, pos=(4, 0), span=(1, 3), flag=wx.EXPAND | wx.ALL, border=5)
        sizer.Add(self.gs_flags_box, pos=(5, 0), span=(1, 3), flag=wx.EXPAND | wx.ALL, border=5)
        sizer.Add(self.convert_button, pos=(6, 1), flag=wx.EXPAND | wx.ALL, border=5)
        sizer.Add(self.compression_type_label, pos=(7, 0), flag=wx.ALL, border=5)
        sizer.Add(self.compression_type_combo, pos=(7, 1), flag=wx.EXPAND | wx.ALL, border=5)
        sizer.Add(self.output_text, pos=(8,0), span=(1,3), flag=wx.EXPAND | wx.ALL, border=5)


        self.panel.SetBackgroundColour(self.background_color)
        self.panel.SetSizer(sizer)
        self.panel.Layout()
        self.Centre()
        self.Show(True)
        self.Bind(wx.EVT_BUTTON, self.on_browse_input, self.browse_input_button)
        self.Bind(wx.EVT_BUTTON, self.on_browse_output, self.browse_output_button)
        self.Bind(wx.EVT_BUTTON, self.on_convert, self.convert_button)
        self.action_combo.Bind(wx.EVT_COMBOBOX, self.on_action_changed)



    def on_browse_input(self, event):
        with wx.DirDialog(self, "Choose input directory", style=wx.DD_DEFAULT_STYLE | wx.DD_NEW_DIR_BUTTON) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self.input_dir_edit.SetValue(dlg.GetPath())
                self.save_setting("input_dir", dlg.GetPath())

    def on_browse_output(self, event):
        with wx.DirDialog(self, "Choose output directory", style=wx.DD_DEFAULT_STYLE | wx.DD_NEW_DIR_BUTTON) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self.output_dir_edit.SetValue(dlg.GetPath())
                self.save_setting("output_dir", dlg.GetPath())

    def on_convert(self, event):
        pdf_dir = self.input_dir_edit.GetValue()
        output_dir = self.output_dir_edit.GetValue()
        pdftotext_path = self.pdftotext_path_edit.GetValue()
        action = self.action_combo.GetValue()

        # Check for existing files in the output directory and prompt the user
        if self.handle_existing_files(output_dir):
            return  # Conversion aborted if the user chooses not to proceed

        gs_flags = []
        if self.safer_checkbox.IsChecked():
            gs_flags.append("-dSAFER")
        if self.verbose_checkbox.IsChecked():
            gs_flags.append("-v")

        self.Update()
        self.panel.Refresh()


        try:
            if action == "Convert to Text":
                self.convert_text(pdf_dir, output_dir, pdftotext_path)
            elif action == "Compress PDF":
                self.compress_pdfs(pdf_dir, output_dir, self.selected_quality, gs_flags)
            elif action == "Decompress PDF":
                self.decompress_pdfs(pdf_dir, output_dir)
            compression_type = self.compression_type_combo.GetValue()
            if compression_type:
                self.compress_output(output_dir, compression_type)
            self.show_job_summary(pdf_dir, output_dir) #moved job summary to the end
        except Exception as e:
            logging.exception("An unexpected error occurred during conversion.")
            wx.MessageBox(f"An unexpected error occurred: {e}", "Error", wx.OK | wx.ICON_ERROR)


        self.Update()
        self.panel.Refresh()
        self.save_setting("compression_quality", self.selected_quality)

    def convert_text(self, pdf_dir, output_dir, pdftotext_path):
        convert_pdfs_to_text(pdf_dir, output_dir, pdftotext_path, self.output_text)


    def compress_pdfs(self, pdf_dir, output_dir, quality, gs_flags):
        self.run_process(pdf_dir, output_dir, "/usr/bin/gs", "Compress PDF", quality=quality, gs_flags=gs_flags)

    def decompress_pdfs(self, pdf_dir, output_dir):
        self.run_process(pdf_dir, output_dir, "/usr/bin/qpdf", "Decompress PDF")

    def run_process(self, pdf_dir, output_dir, program_path, action, quality="ebook", gs_flags=None):
        try:
            pdf_files = find_pdfs_recursive(pdf_dir)
            total_files = len(pdf_files)
            if not total_files:
                wx.MessageBox("No PDF files found.", "Info", wx.OK | wx.ICON_INFORMATION)
                return

            for i, pdf_file in enumerate(pdf_files):
                try:
                    process = self.create_process(pdf_file, output_dir, program_path, action, quality, gs_flags)
                    self.redirect_output(process)
                    wx.Yield()

                except Exception as e:
                    logging.exception(f"Error processing '{pdf_file}': {e}")
                    wx.MessageBox(f"Error processing '{pdf_file}': {e}", "Error", wx.OK | wx.ICON_ERROR)

        except Exception as e:
            logging.exception("An unexpected error occurred during processing.")
            wx.MessageBox(f"An unexpected error occurred: {e}", "Error", wx.OK | wx.ICON_ERROR)

    def create_process(self, pdf_file, output_dir, program_path, action, quality="ebook", gs_flags=None):
        relative_path = os.path.relpath(pdf_file, self.input_dir_edit.GetValue())
        output_path = os.path.join(output_dir, relative_path)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if action == "Convert to Text":
            command = [program_path, "-layout", "-nopgbrk", "-enc", "UTF-8", pdf_file, output_path[:-4] + ".txt"]
        elif action == "Compress PDF":
            compressed_path = os.path.join(output_path[:-4] + ".pdf")
            command = [program_path, "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.4",
                       f"-dPDFSETTINGS=/{quality}", "-dNOPAUSE", "-dQUIET", "-dBATCH",
                       "-sOutputFile=" + compressed_path, pdf_file]
            command.extend(gs_flags or [])
        elif action == "Decompress PDF":
            decompressed_path = os.path.join(output_path[:-4] + ".pdf")
            command = [program_path, "--linearize", pdf_file, decompressed_path]
        else:
            raise ValueError(f"Unknown action: {action}")

        return subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def redirect_output(self, process):
        while True:
            line = process.stdout.readline()
            if not line:
                break
            wx.CallAfter(self.output_text.AppendText, line)

            error_line = process.stderr.readline()
            if error_line:
                wx.CallAfter(self.output_text.AppendText, f"\n[Error]: {error_line.strip()}")

        process.wait()

    def on_action_changed(self, event):
        action = self.action_combo.GetValue()
        self.quality_group.Show(action == "Compress PDF")
        self.panel.Layout()

    def on_quality_selected(self, event):
        radio_button = event.GetEventObject()
        self.selected_quality = radio_button.quality
        self.save_setting("compression_quality", self.selected_quality)

    def load_settings(self, config_file):
        try:
            with open(config_file, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                "input_dir": ".",
                "output_dir": ".",
                "pdftotext_path": "/usr/bin/pdftotext",
                "compression_quality": "ebook" #default compression quality
            }

    def save_setting(self, key, value):
        self.settings[key] = value
        with open("config.json", "w") as f:
            json.dump(self.settings, f, indent=4)

    def handle_existing_files(self, output_dir):
        if os.listdir(output_dir):
            dlg = wx.MessageDialog(None, "Output directory is not empty. Choose an action:", "Confirm Action", wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION)
            dlg.SetYesNoLabels("Overwrite", "Delete All")
            result = dlg.ShowModal()
            dlg.Destroy()
            if result == wx.ID_YES:
                return False  #Overwrite existing files
            elif result == wx.ID_NO:
                try:
                    for filename in os.listdir(output_dir):
                        file_path = os.path.join(output_dir, filename)
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                    return False
                except OSError as e:
                    wx.MessageBox(f"Error deleting files: {e}", "Error", wx.OK | wx.ICON_ERROR)
                    return True
            else:
                return True  # Cancel conversion
        return False

    def show_job_summary(self, input_dir, output_dir):
        try:
            num_files = len(find_pdfs_recursive(input_dir))
            num_folders = len([f for f in os.listdir(input_dir) if os.path.isdir(os.path.join(input_dir, f))])

            initial_size = get_folder_size(input_dir)
            final_size = get_folder_size(output_dir)

            summary_text = (f"Job Summary:\n\n"
                            f"Input Directory: {input_dir}\n"
                            f"Output Directory: {output_dir}\n"
                            f"Number of Files Processed: {num_files}\n"
                            f"Number of Folders: {num_folders}\n"
                            f"Initial Size: {format_bytes(initial_size)}\n"
                            f"Final Size: {format_bytes(final_size)}")
            wx.MessageBox(summary_text, "Job Summary", wx.OK | wx.ICON_INFORMATION)
        except Exception as e:
            logging.error(f"Error generating job summary: {e}")
            wx.MessageBox(f"Error generating job summary: {e}", "Error", wx.OK | wx.ICON_ERROR)

    def compress_output(self, output_dir, compression_type):
        try:
            output_filename = os.path.join(os.path.dirname(output_dir), os.path.basename(output_dir) + f".{compression_type}")
            if compress_folder(output_dir, output_filename, compression_type):
                wx.MessageBox(f"Output folder '{output_dir}' compressed to '{output_filename}'.", "Success", wx.OK | wx.ICON_INFORMATION)
            else:
                wx.MessageBox(f"Error compressing output folder.", "Error", wx.OK | wx.ICON_ERROR)
        except Exception as e:
            logging.exception(f"An unexpected error occurred during output compression: {e}")
            wx.MessageBox(f"An unexpected error occurred during output compression: {e}", "Error", wx.OK | wx.ICON_ERROR)

app = wx.App()
frame = PDFConverterGUI(None)
if frame:
    app.MainLoop()
