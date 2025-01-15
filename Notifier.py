import os
from win10toast import ToastNotifier

def notify(title, message):
    notifier = ToastNotifier()
    notifier.show_toast(
        title=title, 
        msg=message, 
        duration=5, 
        threaded=True
    )


	#ToastNotifier.remove(os.getpid())

