import logging
from typing import Union, Optional

from fastapi import HTTPException

from utils import EX, add_fonts
from schemas.irrigation import *

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_irrigation_operations(data: dict) -> Optional[List[IrrigationOperation]]:
    """
    Parse list of irrigation operations from JSON data
    """
    try:
        return [IrrigationOperation.model_validate(item) for item in data]
    except Exception as e:
        logger.error(f"Error parsing irrigation operations: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Reporting service failed during PDF generation. File is not correct JSON. {e}",
        )


def create_pdf_from_operations(operations: List[IrrigationOperation]):
    """
    Create PDF report from irrigation operations
    """
    pdf = EX()
    pdf.add_page()
    add_fonts(pdf)
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_title("Irrigation Operations Report")
    EX.ln(pdf)

    pdf.set_font("FreeSerif", "B", 10)
    pdf.cell(40, 10, "Irrigation Operations Report")
    pdf.ln(10)

    for op in operations:
        # Operation Header
        pdf.set_font("FreeSerif", "B", 9)
        pdf.cell(0, 10, f"Operation: {op.title}", ln=True)

        # Activity Type
        activity_type = op.activityType.get(
            "@id", "N/A"
        )  # You can adjust this to extract the specific part you need
        pdf.set_font("FreeSerif", "B", 9)
        pdf.cell(0, 10, f"Activity Type: {activity_type}", ln=True)

        # Details
        pdf.set_font("FreeSerif", "", 9)
        pdf.multi_cell(0, 10, f"Details: {op.details}")
        pdf.ln(5)

        # Parcel ID extraction
        parcel_id = (
            op.operatedOn.get("@id", "N/A").split(":")[3] if op.operatedOn else "N/A"
        )
        pdf.cell(0, 10, f"Operated on Parcel: {parcel_id}", ln=True)

        # Date and Time
        pdf.cell(
            0,
            10,
            f"Start: {op.hasStartDatetime if op.hasStartDatetime else 'N/A'}",
            ln=True,
        )
        pdf.cell(
            0, 10, f"End: {op.hasEndDatetime if op.hasEndDatetime else 'N/A'}", ln=True
        )

        # Applied Amount
        pdf.cell(
            0,
            10,
            f"Applied Amount: {op.hasAppliedAmount.numericValue} {op.hasAppliedAmount.unit}",
            ln=True,
        )

        # Irrigation System
        pdf.cell(0, 10, f"Irrigation System: {op.usesIrrigationSystem}", ln=True)

        # Responsible Agent
        pdf.cell(
            0,
            10,
            f"Responsible Agent: {op.responsibleAgent if op.responsibleAgent else 'N/A'}",
            ln=True,
        )

        # Machinery IDs (if any)
        if op.usesAgriculturalMachinery:
            machinery_ids = ", ".join(
                [
                    machinery.get("@id", "N/A").split(":")[3]
                    for machinery in op.usesAgriculturalMachinery
                ]
            )
            pdf.cell(0, 10, f"Machinery IDs: {machinery_ids}", ln=True)

        pdf.ln(10)

    return pdf


def process_irrigation_data(json_data: dict):
    """
    Process irrigation data and generate PDF report
    """
    operations = parse_irrigation_operations(json_data)

    if not operations:
        return None

    pdf = create_pdf_from_operations(operations)

    return pdf
