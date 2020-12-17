from base.object_detector import ObjectDetector
from base.gaze_follower import GazeFollower
# from base.face_recognizer2 import FaceRecognizer
from base.face_detector2 import FaceDetector
from unimodal.imagestream import ImageStream

import numpy as np
import cv2
import PIL

import sys


def run(url, queue, barrier):
    ''' Main function to be executed by a process.
    '''
    monitor = VisualMonitor(None)

    if barrier is not None: # debug
        barrier.wait()

    monitor.start(url, queue)


class VisualMonitor:

    def __init__(self, child_embedding):
        print('Initializing visual models...')

        self.child_embedding = child_embedding
        print('child embedding')

        self.object_detector = ObjectDetector()
        self.id_class_mappings = self.object_detector.id_to_classname_mappings()
        print('object detector')

        self.gaze_follower = GazeFollower('../model_weights/visatt.pt')
        print('gaze follower')

        # # self.face_recognizer = FaceRecognizer(child_embedding)
        self.face_detector = FaceDetector()
        print('face detector')

        print('Initializing visual models done!')
        sys.stdout.flush() # debug


    def start(self, url, queue):
        ''' Main method
        '''
        print('start VisualMonitor')
        
        imagestream = ImageStream(url, buffer_length=8)
        imagestream.start()

        while 1:
            frames = imagestream.dump()
            frame = frames[-1] # most recent?
            results = self.predict_single_frame(frame)

            queue.put(results)


    def predict_single_frame(self, frame):
        """ Predicts the child's attended target for a single frame,
            and returns relevant outputs from intermediate predictions as well.

            frame: RGB frame
        """
        outputs = {
            'from': 'image',
            'image': frame,
            'object_bboxes': [],
            'object_confidences': [],
            'object_classnames': [],
            'face_bboxes': [],
            'gaze_targets': []
        }

        frame_pil = PIL.Image.fromarray(frame.astype('uint8'), 'RGB')
        
        face_bboxes = self.face_detector.predict(frame)

        objects = self.object_detector.predict(frame)

        instances = objects['instances'] # only key
        fields = instances.get_fields()
        object_bboxes = fields['pred_boxes'].tensor.cpu().numpy()
        class_ids = fields['pred_classes']
        scores = fields['scores'].cpu().numpy()
        classes = list(map(lambda x: self.id_class_mappings[x], class_ids))

        outputs['object_bboxes'].extend(object_bboxes)
        outputs['object_confidences'].extend(scores)
        outputs['object_classnames'].extend(classes)
        outputs['face_bboxes'].extend(face_bboxes)
        
        if face_bboxes != []:
            for face_bbox in face_bboxes:
                focus_point = self.gaze_follower.predict_gaze(frame_pil, 
                                                              face_bbox)
                outputs['gaze_targets'].append(focus_point)

        return outputs
