import time
import pyautogui
import keyboard

print("Move your mouse to the position you want.")
print("Press SPACE to capture the position.")
print("Press ESC anytime to stop.")

keyboard.wait("space")

x, y = pyautogui.position()
print(f"Captured position: x={x}, y={y}")

print("Clicking every 30 seconds...")

while True:
    if keyboard.is_pressed("esc"):
        print("Stopped.")
        break

    pyautogui.click(x=x, y=y, button="left")
    print(f"Clicked at ({x}, {y})")

    # Wait 30 seconds, but keep checking ESC
    for _ in range(300):
        if keyboard.is_pressed("esc"):
            print("Stopped.")
            raise SystemExit

        time.sleep(0.1)