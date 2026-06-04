# -*- coding: utf-8 -*-
import os
import sys
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum

class PrinterType(Enum):
    USB = "usb"
    SERIAL = "serial"
    NETWORK = "network"
    PDF = "pdf"
    IMAGE = "image"

@dataclass
class PrinterInfo:
    id: str
    name: str
    type: PrinterType
    connection_string: str
    is_default: bool = False
    capabilities: List[str] = None

    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []

class PrinterManager:
    def __init__(self):
        self.printers: List[PrinterInfo] = []
        self._detect_printers()
    
    def _detect_printers(self):
        self.printers.clear()
        # طابعة PDF افتراضية
        self.printers.append(PrinterInfo(
            id="pdf:default",
            name="حفظ كـ PDF",
            type=PrinterType.PDF,
            connection_string=""
        ))
        # إضافة طابعة صورة
        self.printers.append(PrinterInfo(
            id="image:png",
            name="حفظ كـ صورة PNG",
            type=PrinterType.IMAGE,
            connection_string=""
        ))
        # محاولة كشف طابعات النظام (في نظام التشغيل الفعلي)
        try:
            from PyQt5.QtPrintSupport import QPrinterInfo
            for printer in QPrinterInfo.availablePrinters():
                self.printers.append(PrinterInfo(
                    id=f"qt:{printer.printerName()}",
                    name=printer.printerName(),
                    type=PrinterType.NETWORK,
                    connection_string=printer.printerName()
                ))
        except:
            pass
    
    def get_default_printer(self) -> Optional[PrinterInfo]:
        for p in self.printers:
            if p.is_default:
                return p
        return self.printers[0] if self.printers else None
    
    def get_printer(self, printer_id: str) -> Optional[PrinterInfo]:
        for p in self.printers:
            if p.id == printer_id:
                return p
        return None
    
    def save_default_printer(self, printer_id: str):
        for p in self.printers:
            p.is_default = (p.id == printer_id)
        from PyQt5.QtCore import QSettings
        settings = QSettings("Hawaa", "Accounting")
        settings.setValue("printer/default", printer_id)
    
    def load_default_printer(self):
        from PyQt5.QtCore import QSettings
        settings = QSettings("Hawaa", "Accounting")
        printer_id = settings.value("printer/default", "")
        if printer_id:
            for p in self.printers:
                p.is_default = (p.id == printer_id)
