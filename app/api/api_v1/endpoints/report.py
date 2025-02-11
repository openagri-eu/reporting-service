import json
import uuid
from json import JSONDecodeError
from fastapi import APIRouter, File, Depends, HTTPException, UploadFile, Response
from api import deps
from core import settings
from utils.farm_calendar_report import process_farm_calendar_data
from utils.irrigation_report import process_irrigation_data
from utils.json_handler import make_get_request

router = APIRouter()


@router.post("/irrigation-report/")
async def generate_irrigation_report(
    token=Depends(deps.get_current_user),
    data: UploadFile = None,
):
    """
    Generates Irrigation Report PDF file

    """

    pdf = None
    if not data:
        if not settings.REPORTING_USING_GATEKEEPER:
            raise HTTPException(
                status_code=400,
                detail=f"Data file must be provided if gatekeeper is not used.",
            )

        params = {"format": "json"}
        json_response = make_get_request(
            url=f'{settings.REPORTING_FARMCALENDAR_BASE_URL}{settings.REPORTING_FARMCALENDAR_URLS["irrigations"]}',
            token=token,
            params=params,
        )

        if not json_response:
            raise HTTPException(status_code=400, detail="No Irrigation data found.")

        pdf = process_irrigation_data(json_data=json_response)

    else:
        try:
            pdf = process_irrigation_data(json_data=json.load(data.file))

        except JSONDecodeError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Reporting service failed during PDF generation. File is not correct JSON.",
            )

    if not pdf:
        raise HTTPException(
            status_code=400,
            detail=f"Reporting service failed during PDF generation.",
        )

    headers = {
        "Content-Disposition": "attachment; filename={}-report-{}.pdf".format(
            "irrigation", uuid.uuid4()
        )
    }

    return Response(
        content=bytes(pdf.output()), media_type="application/pdf", headers=headers
    )


@router.post("/compost-report/")
async def generate_generic_observation_report(
    observation_type_name: str,
    token=Depends(deps.get_current_user),
    data: UploadFile = None,
):
    """
    Generates Observation Report PDF file
    possible_names = ["Pesticides", "Irrigation", "Fertilization", "CropStressIndicator", "CropGrowthObservation"]


    """
    print(observation_type_name)
    possible_names = [
        "Pesticides",
        "Irrigation",
        "Fertilization",
        "CropStressIndicator",
        "CropGrowthObservation",
    ]
    if observation_type_name not in possible_names:
        raise HTTPException(
            status_code=400,
            detail=f"Observation type name: {observation_type_name} is not inside supported types: {possible_names}",
        )

    if observation_type_name == "CropGrowthObservation":
        observation_type_name = "Crop Growth Stage Observation"

    if observation_type_name == "CropStressIndicator":
        observation_type_name = "Crop Stress Indicator"

    pdf = None
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
            raise HTTPException(status_code=400, detail="Farm Activities are empty.")

        print(farm_activity_type_info, observations, farm_activities, "here")
        pdf = process_farm_calendar_data(
            activity_type_info=observation_type_name,
            observations=observations,
            farm_activities=farm_activities,
        )

    else:
        try:
            pdf = process_farm_calendar_data(
                activity_type_info=observation_type_name,
                observations=json.load(data.file)["observations"],
                farm_activities=json.load(data.file)["farm_activities"],
            )

        except JSONDecodeError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Reporting service failed during PDF generation. File is not correct JSON.",
            )

    if not pdf:
        raise HTTPException(
            status_code=400,
            detail=f"Reporting service failed during PDF generation.",
        )

    headers = {
        "Content-Disposition": "attachment; filename={}-report-{}.pdf".format(
            "irrigation", uuid.uuid4()
        )
    }

    return Response(
        content=bytes(pdf.output()), media_type="application/pdf", headers=headers
    )
