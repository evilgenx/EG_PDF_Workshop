# PDF Workshop 
<br />
<div align="center">
  <a href="https://github.com/your_username/your-repo-name">
    <img src="images/logo.png" alt="Logo" width="80" height="80"> 
  </a>
  <h3 align="center">PDF Workshop</h3>

  <p align="center">
    A versatile tool to convert, compress, and decompress PDF files.
    <br />
    <a href="https://github.com/your_username/your-repo-name"><strong>Explore the docs »</strong></a>
    <br />
    <br />
    <a href="https://github.com/your_username/your-repo-name">View Demo</a>
    ·
    <a href="https://github.com/your_username/your-repo-name/issues">Report Bug</a>
    ·
    <a href="https://github.com/your_username/your-repo-name/issues">Request Feature</a>
  </p>
</div>


## About The Project

PDF Workshop is a user-friendly GUI application built with Python and wxPython that simplifies common PDF manipulation tasks. It provides a convenient way to:

* **Convert PDFs to text:** Extract text content from PDFs while preserving the original layout.
* **Compress PDFs:** Reduce the file size of PDFs using various compression levels.
* **Decompress PDFs:** Optimize PDFs for faster viewing and printing.
* **Batch process multiple files:**  Efficiently handle large numbers of PDF documents.

## Features

* Convert PDFs to text with layout preservation
* Compress PDFs with customizable quality settings (screen, ebook, prepress, default)
* Decompress PDFs for optimized viewing
* Batch processing of PDF files within a directory and its subdirectories
* Ghostscript flags for advanced compression control (Safer Mode, Verbose Mode)
* Compress output folder to zip, 7z, or tar.gz archive
* User-friendly graphical interface
* Detailed job summary with file and size information

## Getting Started

### Prerequisites

Before running PDF Workshop, ensure you have the following dependencies installed:

* **Python 3.6 or higher**
* **wxPython:** `pip install wxPython`
* **poppler-utils:**  (Provides `pdftotext`)
    * On Debian/Ubuntu: `sudo apt-get install poppler-utils` 
    * On macOS: `brew install poppler`
* **Ghostscript:**
    * On Debian/Ubuntu: `sudo apt-get install ghostscript`
    * On macOS: `brew install ghostscript`
* **qpdf:**
    * On Debian/Ubuntu: `sudo apt-get install qpdf`
    * On macOS: `brew install qpdf`

### Installation

1. Clone the repository:
   ```sh
   git clone [invalid URL removed]
