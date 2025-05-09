import json
import logging
import os
from typing import Union
from fastapi import HTTPException

from core import settings
from schemas.compost import *
from utils import EX, add_fonts
from utils.json_handler import make_get_request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FarmCalendarData:
    """Class to process and store connected farm calendar data"""

    def __init__(
        self,
        activity_type_info: str,
        observations: Union[dict, str],
        farm_activities: Union[dict, str],
    ):
        self.activity_type = activity_type_info
        try:
            self.observations = [
                CropObservation.model_validate(obs) for obs in observations
            ]
            self.operations = [Operation.model_validate(act) for act in farm_activities]

        except Exception as e:
            logger.error(f"Error parsing farm calendar data: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Reporting service failed during data validation. File is not correct JSON. {e}",
            )


def create_farm_calendar_pdf(calendar_data: FarmCalendarData) -> EX:
    """Create PDF report from farm calendar data"""
    pdf = EX()
    add_fonts(pdf)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_title("Farm Calendar Report")

    EX.ln(pdf)
    pdf.set_font("FreeSerif", "B", 14)
    pdf.cell(0, 10, "Farm Calendar Report", ln=True, align="C")
    pdf.ln(5)

    pdf.set_font("FreeSerif", "B", 12)
    pdf.cell(0, 10, "Activity Type Information", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 10, f"Type: {calendar_data.activity_type}", ln=True)

    pdf.set_font("FreeSerif", "B", 12)
    pdf.cell(0, 10, "Operations and Observations", ln=True)
    pdf.ln(5)

    for operation in calendar_data.operations:
        pdf.set_font("FreeSerif", "B", 10)
        pdf.cell(0, 10, f"Operation: {operation.title}", ln=True)

        pdf.set_font("FreeSerif", "", 9)
        pdf.multi_cell(0, 10, f"Details: {operation.details}", ln=True)

        if operation.hasStartDatetime:
            pdf.cell(
                0,
                10,
                f"Start: {operation.hasStartDatetime}",
                ln=True,
            )

        if operation.hasEndDatetime:
            pdf.cell(
                0,
                10,
                f"End: {operation.hasEndDatetime}",
                ln=True,
            )

        (
            pdf.cell(0, 10, f"Responsible: {operation.responsibleAgent}", ln=True)
            if operation.responsibleAgent
            else None
        )
        pdf.cell(0, 10, f"Type: {operation.activityType.get('@id', 'N/A')}", ln=True)

        if operation.usesAgriculturalMachinery:
            machinery_ids = ", ".join(
                [
                    machinery.get("@id", "N/A").split(":")[3]
                    for machinery in operation.usesAgriculturalMachinery
                ]
            )
            pdf.cell(0, 10, f"Machinery IDs: {machinery_ids}", ln=True)

        for x in calendar_data.observations:
            pdf.set_font("FreeSerif", "B", 10)
            pdf.cell(0, 10, "Observations:", ln=True)
            pdf.set_font("FreeSerif", "", 10)
            (
                pdf.cell(0, 10, f"Value: {x.hasResult.hasValue}", ln=True)
                if x.hasResult
                else None
            )
            (
                pdf.cell(0, 10, f"Value unit: {x.hasResult.unit}", ln=True)
                if x.hasResult
                else None
            )
            (
                pdf.cell(0, 10, f"Property: {x.relatesToProperty}", ln=True)
                if x.relatesToProperty
                else None
            )
            (
                pdf.cell(0, 10, f"Observed Property: {x.observedProperty}", ln=True)
                if x.observedProperty
                else None
            )
            pdf.cell(0, 10, f"Details: {x.details}", ln=True)

            if x.hasStartDatetime:
                pdf.cell(
                    0,
                    10,
                    f"Start: {x.hasStartDatetime}",
                    ln=True,
                )

            if x.hasEndDatetime:
                pdf.cell(
                    0,
                    10,
                    f"Start: {x.hasEndDatetime}",
                    ln=True,
                )

            (
                pdf.cell(0, 10, f"Responsible: {x.responsibleAgent}", ln=True)
                if x.responsibleAgent
                else None
            )

            if x.usesAgriculturalMachinery:
                machinery_ids = ", ".join(
                    [
                        machinery.get("@id", "N/A").split(":")[3]
                        for machinery in x.usesAgriculturalMachinery
                    ]
                )
                pdf.cell(0, 10, f"Machinery IDs: {machinery_ids}", ln=True)

        pdf.ln(10)

    return pdf


def process_farm_calendar_data(
    observation_type_name: str,
    token: dict[str, str],
    pdf_file_name: str,
    data=None,
) -> None:
    """
    Process farm calendar data and generate PDF report
    """
    try:
        if not data:
            if not settings.REPORTING_USING_GATEKEEPER:
                raise HTTPException(
                    status_code=400,
                    detail=f"Data file must be provided if gatekeeper is not used.",
                )

            params = {"format": "json", "name": observation_type_name}
            farm_activity_type_info = make_get_request(
                url=f'{settings.REPORTING_FARMCALENDAR_BASE_URL}{settings.REPORTING_FARMCALENDAR_URLS["activity_types"]}',
                token=token,
                params=params,
            )

            if not farm_activity_type_info:
                raise HTTPException(status_code=400, detail="Activity Type API failed.")

            del params["name"]
            params["activity_type"] = farm_activity_type_info[0]["@id"].split(":")[3]

            observations = make_get_request(
                url=f'{settings.REPORTING_FARMCALENDAR_BASE_URL}{settings.REPORTING_FARMCALENDAR_URLS["observations"]}',
                token=token,
                params=params,
            )

            if not observations:
                raise HTTPException(status_code=400, detail="Observations are empty.")

            farm_activities = make_get_request(
                url=f'{settings.REPORTING_FARMCALENDAR_BASE_URL}{settings.REPORTING_FARMCALENDAR_URLS["activities"]}',
                token=token,
                params=params,
            )

            if not farm_activities:
                raise HTTPException(
                    status_code=400, detail="Farm Activities are empty."
                )

            calendar_data = FarmCalendarData(
                activity_type_info=observation_type_name,
                observations=observations,
                farm_activities=farm_activities,
            )
        else:
            dt = json.load(data.file)
            calendar_data = FarmCalendarData(
                activity_type_info=observation_type_name,
                observations=dt["observations"],
                farm_activities=dt["farm_activities"],
            )

        pdf = create_farm_calendar_pdf(calendar_data)
        pdf_dir = f"{settings.PDF_DIRECTORY}{pdf_file_name}"
        os.makedirs(os.path.dirname(f"{pdf_dir}.pdf"), exist_ok=True)
        pdf.output(f"{pdf_dir}.pdf")

    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Error processing farm calendar data: {str(e)}"
        )
