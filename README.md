# TireWorldInventory

TireWorldInventory is a custom-built, web-based inventory management system designed specifically for multi-location tire shops.  
It allows for real-time inventory monitoring, transfer management, and detailed reporting between retail stores and a centralized warehouse.

---

## Table of Contents

- [About the Project](#about-the-project)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Future Plans](#future-plans)

---

## About the Project

TireWorldInventory was developed to replace outdated, manual tracking systems used across multiple tire store locations.  
It brings inventory management into a single, easy-to-use web application, giving real-time visibility into stock levels, transfers between stores, and warehouse operations.  
The system is built around the day-to-day needs of tire shops, making it easier to manage inventory, reduce errors, and keep operations running smoothly across multiple locations.

---

## Features

- **Multi-Location Inventory View**: Filter and monitor inventory by individual store or warehouse  
- **Barcode Scanning**: Camera-based scanning to add or check inventory items  
- **Transfer Requests**: Initiate, approve, or deny stock transfers between locations  
- **Admin Controls**: Two-step approval chain for warehouse distribution  
- **Sales & Usage Reports**: Exportable reports for daily sales, inventory pulls, and usage trends  
- **Inventory Tracking**: Monitor tire sizes, brands, models, and quantities across multiple locations  
- **Responsive UI**: Mobile-friendly dashboard with dropdown navigation for ease of use

---

## Tech Stack

- **Backend**: Python (Flask, Flask-SQLAlchemy)  
- **Frontend**: HTML5, CSS3, JavaScript  
- **Database**: SQLite  
- **Tools**: Git, GitHub, VS Code, PyInstaller (for local builds)

---

## Getting Started

To run locally:

```bash
# Clone the repository
git clone https://github.com/Varioli/TireWorldInventory
cd TireWorldInventory

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

Once the app is running, open your browser and go to:
```
http://localhost:5000
```

---

## Future Plans

- **User Authentication and Permissions** (multi-user login with role-based access)  
- **Cloud Deployment** for real-time cross-location access  
- **Low-Inventory Alerts** and automated reorder prompts  
- **Expanded Reporting** with profit margins and forecasting  
- **Direct Manufacturer API Integration** for product information and stock levels

---
