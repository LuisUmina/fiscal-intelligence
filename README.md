# Fiscal Intelligence

**Advanced batch processing platform for Peruvian fiscal data extraction, consultation, and reporting.**

A modern, user-friendly desktop application that automates large-scale RUC (Registro Único de Contribuyente) data extraction from tax declaration files, validates them against Peru's SUNAT registry, and generates comprehensive Excel reports.

---

## 🎯 Purpose & Use Cases

**Fiscal Intelligence** simplifies fiscal data management for:
- **Tax Compliance Teams** — Validate bulk RUC listings against official SUNAT records
- **Data Analysts** — Extract structured fiscal data for reporting and analysis
- **Corporate Compliance Officers** — Generate consolidated reports on representative, employee, and establishment data
- **Auditors** — Verify organizational structures and regulatory compliance across multiple entities

Designed to process high volumes of tax declaration files (801 and 804 formats) in minutes while maintaining data integrity and compliance standards.

---

## ⚡ Key Features

✅ **Batch Processing** — Process hundreds of TXT files simultaneously  
✅ **Real-time Progress Tracking** — Live status indicators, KPI metrics, and activity logs  
✅ **Multi-layer Data Extraction** — Automated RUC validation and SUNAT registry consultation  
✅ **Comprehensive Reporting** — Export to Excel with pre-formatted sheets  
✅ **Regulatory Data** — Access to SSCO (Sujetos sin Capacidad Operativa) padron  
✅ **Stop/Pause Control** — Graceful process interruption with state preservation  
✅ **Customizable Paths** — Choose input/output directories dynamically  

---

## 📊 What It Does

1. **Reads** → Parses TXT files in 801/804 format (Peruvian tax declarations)
2. **Extracts** → Identifies unique RUCs from the declarations
3. **Validates** → Queries SUNAT's official API for each RUC:
   - Legal representatives data
   - Employee/worker history
   - Authorized establishments
4. **Enriches** → Retrieves SSCO (Sujetos sin Capacidad Operativa) padron data
5. **Exports** → Generates structured Excel files with formatted headers and data validation

**Output files:**
- `DATOS_RUC.xlsx` — Three-sheet workbook: Representatives, Workers, Establishments
- `Sujetos sin capacidad operativa.xlsx` — Complete SSCO registry

---

## 🛠 Tech Stack

- **Frontend**: CustomTkinter (modern Python GUI framework)
- **Backend**: Python 3.x with async processing
- **Web Scraping**: Requests + BeautifulSoup, Playwright
- **Data Export**: Pandas, OpenPyXL
- **Architecture**: Event-driven processors with thread-safe queue management

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- ~500MB disk space for dependencies and data

### Installation

```bash
# Clone or download the repository
cd fiscal-intelligence

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Application

```bash
python app.py
```

The GUI will launch with input/output folder selectors and a start button.

---

## 📁 Project Structure

```
fiscal-intelligence/
├── app.py                          # Main GUI application (CustomTkinter)
├── config/
│   ├── branding.py                # UI configuration (customizable)
│   ├── settings.py                # SUNAT URLs, field mappings
│   └── logging_config.py
├── src/
│   ├── extractors/               # Data extraction modules
│   │   ├── txt_parser.py         # PLE 801/804 file parsing
│   │   ├── sunat_consulta_ruc.py # SUNAT RUC consultation
│   │   └── sunat_ssco.py         # SSCO padron download
│   ├── processors/               # Business logic orchestration
│   │   └── sunat_pipeline.py     # Main processing pipeline
│   ├── transformers/             # Data transformation
│   │   ├── excel_exporter.py     # Excel file generation
│   │   └── preparar_ssco.py      # SSCO data formatting
│   └── utils/                    # Helpers
│       ├── file_utils.py
│       └── retry.py
├── requirements.txt
└── README.md
```

---

## 🔄 Processing Pipeline

```
Input TXT Files
    ↓
[1] Read & parse → Extract RUCs (2% progress)
    ↓
[2] Initialize SUNAT session (4% progress)
    ↓
[3] Batch consult Representatives, Workers, Establishments (12-72% progress)
    ↓
[4] Download SSCO padron (72-78% progress)
    ↓
[5] Format & export to Excel (78-95% progress)
    ↓
Output Excel Files ✓
```

Real-time KPIs tracked:
- TXT files detected
- Unique RUCs extracted
- Successful queries
- Errors/missing data

---

## 📝 Configuration

Edit `config/branding.py` to customize UI text:

```python
WINDOW_TITLE = "Fiscal Intelligence"
BRAND_NAME = "FI"
MAIN_TITLE = "Fiscal Intelligence"
SUBTITLE = "Advanced Data Platform"
```

Edit `config/settings.py` to modify SUNAT endpoints and field mappings.

---

## ⚙️ Requirements

See `requirements.txt`. Key dependencies:
- `customtkinter` — Modern GUI framework
- `pandas` — Data manipulation
- `openpyxl` — Excel generation
- `requests` — HTTP client
- `beautifulsoup4` — HTML parsing
- `playwright` — Browser automation (optional)

---

## 📋 Example Workflow

1. **Prepare input** — Place PLE 801/804 TXT files in a folder
2. **Launch app** → `python app.py`
3. **Select folders** → Choose input folder with TXT files, output folder for Excel
4. **Start process** → Click "Iniciar proceso completo" button
5. **Monitor** → Watch real-time progress, logs, and KPIs
6. **Export** → Retrieve Excel files from output folder
7. **Stop if needed** → Click "Detener proceso" to pause gracefully

---

## 🔒 Data Privacy & Security

- No data is stored persistently; processing is ephemeral
- SUNAT credentials are session-based (managed by Requests library)
- Input/output folders are configurable and local
- `.gitignore` excludes sensitive input/output data from version control

---

## ℹ️ Project Scope

This project is a personal implementation of a web automation and data processing tool designed to extract publicly available information from government portals.

It was built for learning and demonstration purposes only. No confidential data or proprietary systems are involved.

---

## 💡 Future Enhancements

- [ ] Retry logic with exponential backoff for failed queries
- [ ] Multi-threaded parallel RUC consultation
- [ ] Advanced filtering and search capabilities
- [ ] REST API wrapper for integration
- [ ] Database backend for historical data
- [ ] CSV export option
- [ ] Internationalization (i18n) support

---

## 📧 Contact & Support

For questions, suggestions, or issues, feel free to reach out or submit a GitHub issue.

---

**Version**: v1.0  
**Last Updated**: 2026
