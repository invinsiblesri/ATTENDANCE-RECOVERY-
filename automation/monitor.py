from notification.notifier import send_notification
attendance = {
    "Period 1": "Present",
    "Period 2": "Absent",
    "Period 3": "Present",
    "Period 4": "Present",
    "Period 5": "Absent"
}

print("Today's Attendance")
print("-------------------------")

for period, status in attendance.items():
    print(period, ":", status)
    total_periods = len(attendance)

present_periods = 0

for period in attendance:
    if attendance[period] == "Present":
        present_periods += 1

percentage = (present_periods / total_periods) * 100

print("-------------------------")
print("Total Periods:", total_periods)
print("Present Periods:", present_periods)
print("Attendance:", percentage, "%")

if percentage < 75:
    risk = "HIGH"

elif percentage < 80:
    risk = "MEDIUM"

else:
    risk = "LOW"

print("Risk:", risk)

if risk == "HIGH":

    message = (
        f"Your attendance is {percentage:.1f}%. "
        "Your attendance is below the required percentage. "
        "Please attend the upcoming periods regularly."
    )

    send_notification(
        "S001",
        message,
        "HIGH"
    )