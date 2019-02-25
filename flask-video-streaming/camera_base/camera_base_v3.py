import time
import threading
try:
    from greenlet import getcurrent as get_ident
except ImportError:
    try:
        from thread import get_ident
    except ImportError:
        from _thread import get_ident


from web_socket import  websocket_client

class CameraEvent(object):
    """An Event-like class that signals all active clients when a new frame is
    available.
    """
    def __init__(self):
        self.events = {}

    def wait(self):
        """Invoked from each client's thread to wait for the next frame."""
        ident = get_ident()
        if ident not in self.events:
            # this is a new client
            # add an entry for it in the self.events dict
            # each entry has two elements, a threading.Event() and a timestamp
            self.events[ident] = [threading.Event(), time.time()]
        return self.events[ident][0].wait()

    def set(self):
        """Invoked by the camera thread when a new frame is available."""
        now = time.time()
        remove = None
        for ident, event in self.events.items():
            if not event[0].isSet():
                # if this client's event is not set, then set it
                # also update the last set timestamp to now
                event[0].set()
                event[1] = now
            else:
                # if the client's event is already set, it means the client
                # did not process a previous frame
                # if the event stays set for more than 5 seconds, then assume
                # the client is gone and remove it
                if now - event[1] > 5:
                    remove = ident
        if remove:
            del self.events[remove]

    def clear(self):
        """Invoked from each client's thread after a frame was processed."""
        self.events[get_ident()][0].clear()


class BaseCamera(object):
    # 摄像头帧的获取线程
    thread = None  # background thread that reads frames from camera
    frame = None  # current frame is stored here by background thread
    last_access = 0  # time of last client access to the camera
    event = CameraEvent()

    # 拿到一帧去识别的线程
    thread_recognize = None
    frame_recognize = None
    last_recognize = 0
    condition = threading.Condition()
    flag = False

    # websocket监听线程
    web_socket_server = None


    def __init__(self, web_socket_server=None):
        """Start the background camera thread if it isn't running yet."""
        self.web_socket_server = web_socket_server
        if BaseCamera.thread is None:
            BaseCamera.last_access = time.time()
            print('线程数：{}'.format(threading.active_count()))
            # start background frame thread
            BaseCamera.thread = threading.Thread(target=self._thread)
            BaseCamera.thread.start()
            print('create frame线程 start')


            BaseCamera.thread_recognize = threading.Thread(target=self._doRecognizeFrame)
            BaseCamera.thread_recognize.start()
            print('frame recognize线程 start')



            print('开始 get frame')
            # wait until frames are available
            while self.get_frame() is None:
                time.sleep(0)



    def get_frame(self):
        """Return the current camera frame."""
        BaseCamera.last_access = time.time()

        # wait for a signal from the camera thread
        #print('wait frame')
        BaseCamera.event.wait()
        BaseCamera.event.clear()
        #print('return frame')
        return BaseCamera.frame

    @staticmethod
    def frames():
        """"Generator that returns frames from the camera."""
        raise RuntimeError('Must be implemented by subclasses.')

    @classmethod
    def _thread(cls):
        """Camera background thread."""
        #print('Starting camera thread.')
        BaseCamera.last_recognize = time.time()
        frames_iterator = cls.frames()
        for frame in frames_iterator:
            #print('create frmae')
            BaseCamera.frame = frame
            BaseCamera.event.set()  # send signal to clients
            time.sleep(0)

            # 间隔一段时间抓一个帧
            if time.time() - BaseCamera.last_recognize > 1:
                if BaseCamera.condition.acquire():
                    #print('start notify recognize ')
                    BaseCamera.condition.notify_all()
                    BaseCamera.condition.release()
                    #print('notify recognize over')

            # if there hasn't been any clients asking for frames in
            # the last 10 seconds then stop the thread
            if time.time() - BaseCamera.last_access > 10:
                frames_iterator.close()
                print('Stopping camera thread due to inactivity.')
                break
        BaseCamera.thread = None

    @classmethod
    def _doRecognizeFrame(cls):
        """Camera background thread."""
        while True:
            if BaseCamera.condition.acquire():
                BaseCamera.last_recognize = time.time()
                BaseCamera.condition.wait()
                websocket_client.notifySubThread(BaseCamera.frame)
                #print("start recognize face over")
                BaseCamera.condition.release()


