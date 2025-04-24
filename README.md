# TireWorld Inventory Management System

A custom-built inventory tracking and distribution system developed as a side project for a multi-location tire shop chain. Designed to solve real-world logistical issues in warehouse management, the system streamlines tire tracking, inter-store transfers, and reporting operations across new and used tire inventory.

---

## Table of Contents

- [About the Project](#about-the-project)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Future Plans](#future-plans)

---

## About the Project

This project was developed independently as a technical challenge and operational solution for TireWorld—a company with several locations managing large volumes of tire inventory. The goal was to replace outdated tracking methods with a centralized, scalable system that supports multiple warehouses, reduces errors, and enhances operational efficiency.

*The project is still in active development.*

---

## Features

- **Multi-Location Inventory View**: Filter inventory by store or warehouse  
- **Barcode Scanning**: Camera-based scanning to check or add stock  
- **Transfer Requests**: Initiate, approve, or deny stock transfers between locations  
- **Admin Controls**: Approval chain for warehouse distribution after manager confirmation  
- **Sales & Pull Reports**: Exportable daily sales, pull trends, and usage reports  
- **Responsive UI**: Mobile-friendly dashboard with dropdown navigation  

---

## Tech Stack

- **Backend**: Python (Flask)  
- **Frontend**: HTML5, CSS3, JavaScript  
- **Database**: SQLite  
- **Tools**: Git, GitHub, VS Code  

---

## Getting Started

To run locally:

```bash
# Clone the repository
git clone https://github.com/Varioli/TireWorldInventory.git
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

- **Integration with tire manufacture APIs** 
- **Multi-user authentication and role-based permissions**  
- **Full mobile app version**  
- **Low-inventory alerts & automated restock prompts**  
- **Cloud deployment for real-time access across locations**  

---