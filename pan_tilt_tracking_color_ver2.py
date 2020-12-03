# USAGE
# python pan_tilt_tracking.py --cascade haarcascade_frontalface_default.xml

# import necessary packages
from multiprocessing import Manager
from multiprocessing import Process
from imutils.video import VideoStream
from thuvien.objcenter import ObjCenter
from thuvien.pid import PID
# import pantilthat as pth
import argparse
import signal
import time
import sys
import cv2
from PCA9685 import PCA9685
import imutils

# define the range for the motors
# servoRange = (-90, 90)
servoRange = (0, 180)
pwm = PCA9685()
pwm.setPWMFreq(50)

max_PAN      = 140
max_TILT     = 120
min_PAN      = 50
min_TILT     = 50

max_rate_TILT = 3
max_rate_PAN  = 3

step_PAN     = 1
step_TILT    = 1
default_PAN_Angel  =50
default_TILT_Angel = 50
global finished_servor_process
finished_servor_process = True

# function to handle keyboard interrupt
def signal_handler(sig, frame):
	# print a status message
	print("[INFO] You pressed `ctrl + c`! Exiting...")

	# disable the servos
	# shut down cleanly
	pwm.exit_PCA9685()

	# exit
	sys.exit()

def obj_center(args, objX, objY, centerX, centerY, found_Object, not_Found_Rect_time):
	# signal trap to handle keyboard interrupt
	signal.signal(signal.SIGINT, signal_handler)

	# start the video stream and wait for the camera to warm up
	vs = VideoStream(src=0).start()
	time.sleep(2.0)

	# initialize the object center finder
	# obj = ObjCenter(args["cascade"])
	obj = ObjCenter("haarcascade_frontalface_default.xml")

	# loop indefinitely
	while True:
		# grab the frame from the threaded video stream and flip it
		# vertically (since our camera was upside down)
		frame = vs.read()
		frame = imutils.resize(frame, width=500)
		# frame = cv2.flip(frame, 1)

		# calculate the center of the frame as this is where we will
		# try to keep the object
		(H, W) = frame.shape[:2]
		
		centerX.value = W // 2
		centerY.value = H // 2

		# 480 x640   - 375x500
		# print("H= "+ str(H) +" W="+str(W))
		# find the object's location
		objectLoc = obj.update(frame, (centerX.value, centerY.value))
		((objX.value, objY.value), rect) = objectLoc
				
		if rect is not None:
			# nếu nhận diện khung mặt thì un-comment
			# (x, y, w, h) = rect
			# cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0),
			# 	2)
			((x, y), radius) = cv2.minEnclosingCircle(rect)
			# nếu nhận diện theo mau sac  thì un-comment
			cv2.circle(frame, (int(x), int(y)), int(radius),
					(0, 255, 255), 2)
			cv2.circle(frame, (int(objX.value), int(objY.value)), 5, (0, 0, 255), -1)
			text = "objX = " + str(objX.value) +" objY= "+ str(objY.value)
			color = (0, 0, 0)
			cv2.putText(frame,text , (20,20) , cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, cv2.LINE_AA)
			found_Object.value = 1	
			not_Found_Rect_time.value = time.time()
			# print(" H= "+ str(H)+" w = " + str(W ))	
		else:
			found_Object.value = 0
			

		# display the frame to the screen
		cv2.imshow("Pan-Tilt Face Tracking", frame)
		cv2.waitKey(1)

#position servos 
def positionServo (servo, angle):
	# os.system("python angleServoCtrl.py " + str(servo) + " " + str(angle))
	pwm.setRotationAngle(servo, angle) 
	# print("[INFO] Positioning servo at GPIO {0} to {1} degrees\n".format(servo, angle))


def set_servos(objX, objY, panAngle, tiltAngle, found_Object, not_Found_Rect_time):
	
	# signal trap to handle keyboard interrupt
	signal.signal(signal.SIGINT, signal_handler)
	# print( " pan.value = "+ str(pan.value)+" tlt.value = " + str(tlt.value ) )

	# loop indefinitely
	while True:
	
# Nếu tìm thấy vật thể nên not_Found_Object ==1
		if (found_Object.value == 1):

			if (objX.value < 180):
				panAngle.value += 3
				if panAngle.value > 140:
					panAngle.value = 140
				positionServo (1, panAngle.value) #PAN

			if (objX.value > 350):
				panAngle.value -= 3
				if panAngle.value < 40:
					panAngle.value = 40
				positionServo (1, panAngle.value)

			if (objY.value > 300):
				tiltAngle.value += 3
				if tiltAngle.value > 120:
					tiltAngle.value = 120
				positionServo (0, tiltAngle.value) #TILT

			if (objY.value < 150):
				tiltAngle.value -= 3
				if tiltAngle.value < 40:
					tiltAngle.value = 40
				positionServo (0, tiltAngle.value)

			time.sleep(0.05)
			print ("[INFO] Object Center coordinates at \
		X0 = {0} and Y0 =  {1}  Pan={2} and tilt = {3}".format(objX.value, objY.value,panAngle.value, tiltAngle.value))
		
		
		else:
			# Nếu không tìm thấy đối tượng hơn 15s  cam sẽ quay về vị trí cũ
			if time.time() - not_Found_Rect_time.value >= 15:
				tiltAngle.value = default_TILT_Angel
				panAngle.value = default_PAN_Angel
				positionServo (1, panAngle.value) #PAN
				positionServo (0, tiltAngle.value) #TILT
				not_Found_Rect_time.value = time.time()
				print("Back to default position")


			

# check to see if this is the main body of execution
if __name__ == "__main__":
	# construct the argument parser and parse the arguments
	ap = argparse.ArgumentParser()
	# ap.add_argument("-c", "--cascade", type=str, required=True,
		# help="path to input Haar cascade for face detection")
	args = vars(ap.parse_args())

	# start a manager for managing process-safe variables
	with Manager() as manager:
		# enable the servos
		pwm.setRotationAngle(1, default_PAN_Angel) #PAN    
		pwm.setRotationAngle(0, default_TILT_Angel) #TILT
		found_Object = manager.Value("i", 0)
		not_Found_Rect_time = manager.Value("f", time.time())
		# set integer values for the object center (x, y)-coordinates
		centerX = manager.Value("i", 100)
		centerY = manager.Value("i", 50)

		# set integer values for the object's (x, y)-coordinates
		objX = manager.Value("i", 50)
		objY = manager.Value("i", 0)

		# pan and tilt values will be managed by independed PIDs
		pan = manager.Value("i", default_PAN_Angel)
		tlt = manager.Value("i", default_TILT_Angel)

		# we have 4 independent processes
		# 1. objectCenter  - finds/localizes the object
		# 2. panning       - PID control loop determines panning angle
		# 3. tilting       - PID control loop determines tilting angle
		# 4. setServos     - drives the servos to proper angles based
		#                    on PID feedback to keep object in center
		processObjectCenter = Process(target=obj_center,
			args=(args, objX, objY, centerX, centerY, found_Object, not_Found_Rect_time))
		processSetServos = Process(target=set_servos, args=(objX, objY, pan, tlt, found_Object, not_Found_Rect_time))

		# start all 4 processes
		processObjectCenter.start()
		processSetServos.start()

		# join all 4 processes
		processObjectCenter.join()
		processSetServos.join()

		# disable the servos
		# shut down cleanly
		pwm.exit_PCA9685()