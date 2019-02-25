import time
import threading

class BaseCamera(object):
    thread_create_frame = None  # background thread that reads frames from camera
    thread_recognize_frame = None
    frame = None  # current frame is stored here by background thread
    last_access = 0.0  # time of last client access to the camera
    last_recognize = 0.0
    condition = threading.Condition()

    def __init__(self):
        if BaseCamera.thread_create_frame is None:
            BaseCamera.last_access = time.time()

            # start background frame thread
            BaseCamera.thread_create_frame = threading.Thread(target=self.doCreateFrame)
            BaseCamera.thread_create_frame.start()

            BaseCamera.thread_recognize_frame = threading.Thread(target=self.doRecognizeFrame)
            BaseCamera.thread_recognize_frame.start()

            # wait until frames are available
            while self.get_frame() is None:
               time.sleep(0)

    def get_frame(self):
        """Return the current camera frame.
        main thread
        """
        print("get condition acquire")
        if BaseCamera.condition.acquire():
            BaseCamera.last_access = time.time()
            print("get frame wait")
            BaseCamera.condition.wait()

            BaseCamera.condition.release()
        # wait for a signal from the camera thread
        print("get frame to client for show")
        return BaseCamera.frame

    def post_frame(self):
        """
        post current frame to server for recognize face
        :return: 
        """
        print('get frame condition acquire')
        if BaseCamera.condition.acquire():
            BaseCamera.last_recognize = time.time()

            BaseCamera.condition.wait()
            BaseCamera.condition.release()
            print("send frame to server for recognize")
        # post data

    @staticmethod
    def frames():
        """"Generator that returns frames from the camera."""
        raise RuntimeError('Must be implemented by subclasses.')

    @classmethod
    def doRecognizeFrame(cls):
        """Camera background thread."""
        print('do recognize frame, Starting recognize thread.')

        while True:
            if (time.time() - BaseCamera.last_access > 1) and BaseCamera.frame is not None:
                BaseCamera.post_frame(cls)
                time.sleep(0)
            else:
                time.sleep(0.6)

            # if there hasn't been any clients asking for frames in
            # the last 10 seconds then stop the thread
            if time.time() - BaseCamera.last_recognize > 10:
                print('Stopping recognize thread due to inactivity.')
                break
        BaseCamera.thread_recognize_frame = None


    @classmethod
    def doCreateFrame(cls):
        """Camera background thread."""
        print('do create frame , Starting camera thread.')
        frames_iterator = cls.frames()
        if BaseCamera.condition.acquire():
            for frame in frames_iterator:
                print('create new frame。')
                BaseCamera.frame = frame
                BaseCamera.condition.notify_all()
                time.sleep(0.1)

                # if there hasn't been any clients asking for frames in
                # the last 10 seconds then stop the thread
                if time.time() - BaseCamera.last_access > 10:
                    frames_iterator.close()
                    print('Stopping camera thread due to inactivity.')
                    break
        BaseCamera.condition.release()
        BaseCamera.thread_create_frame = None