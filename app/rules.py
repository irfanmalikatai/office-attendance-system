def get_attendance_status(
    current_minutes: int,
    office_start_minutes: int,
    grace_minutes: int
):
    """
    Check-in ke time employee Present hai ya Late.
    """

    allowed_minutes = office_start_minutes + grace_minutes

    if current_minutes <= allowed_minutes:
        return "Present"

    return "Late"


def get_worked_hours(check_in, check_out):
    """
    Check-in aur check-out ke darmiyan worked hours calculate karta hai.
    """

    worked_seconds = (check_out - check_in).total_seconds()

    return worked_seconds / 3600


def get_checkout_status(worked_hours: float, half_day_hours: float):
    """
    Worked hours ki basis par Half Day ya Checked Out status deta hai.
    """

    if worked_hours < half_day_hours:
        return "Half Day"

    return "Checked Out"


def get_missing_checkout_status(check_out):
    """
    Check-out missing hai ya nahi.
    """

    if check_out is None:
        return "Missing Check-Out"

    return None


def get_absent_status(has_attendance_record: bool):
    """
    Attendance record na ho to employee Absent hai.
    """

    if not has_attendance_record:
        return "Absent"

    return None