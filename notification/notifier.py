def send_notification(student_id, message, priority="NORMAL"):

    print("\n🔔 NOTIFICATION")
    print("-------------------------")
    print("Student ID:", student_id)
    print("Priority:", priority)
    print("Message:", message)
    print("-------------------------")

    return {
        "student_id": student_id,
        "message": message,
        "priority": priority
    }