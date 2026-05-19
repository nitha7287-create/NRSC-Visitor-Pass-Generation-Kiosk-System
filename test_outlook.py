import win32com.client

try:
    outlook = win32com.client.Dispatch("Outlook.Application")

    mail = outlook.CreateItem(0)

    # Open blank compose window first
    mail.Display()

    # Now set values
    mail.Subject = "Visitor Management Test"

    mail.Body = "Outlook automation working."

    print("✅ Outlook compose window opened")

except Exception as e:
    print("❌ Error:", e)