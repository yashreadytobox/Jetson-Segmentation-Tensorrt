"""
An example that uses TensorRT's Python api to make inferences.
"""
import ctypes
import os
import shutil
import random
import sys
import threading
import time
import cv2
import numpy as np
import pycuda.autoinit
import pycuda.driver as cuda
import tensorrt as trt

CONF_THRESH = 0.5
IOU_THRESHOLD = 0.4


def get_img_path_batches(batch_size, img_dir):
    ret = []
    batch = []
    for root, dirs, files in os.walk(img_dir):
        for name in files:
            if len(batch) == batch_size:
                ret.append(batch)
                batch = []
            batch.append(os.path.join(root, name))
    if len(batch) > 0:
        ret.append(batch)
    return ret


def plot_one_box(x, img, color=None, label=None, line_thickness=None):
    """
    description: Plots one bounding box on image img,
                 this function comes from YoLov5 project.
    param: 
        x:      a box likes [x1,y1,x2,y2]
        img:    a opencv image object
        color:  color to draw rectangle, such as (0,255,0)
        label:  str
        line_thickness: int
    return:
        no return

    """
    tl = (
        line_thickness or round(0.002 * (img.shape[0] + img.shape[1]) / 2) + 1
    )  # line/font thickness
    color = color or [random.randint(0, 255) for _ in range(3)]
    c1, c2 = (int(x[0]), int(x[1])), (int(x[2]), int(x[3]))
    cv2.rectangle(img, c1, c2, color, thickness=tl, lineType=cv2.LINE_AA)
    if label:
        tf = max(tl - 1, 1)  # font thickness
        t_size = cv2.getTextSize(label, 0, fontScale=tl / 3, thickness=tf)[0]
        c2 = c1[0] + t_size[0], c1[1] - t_size[1] - 3
        cv2.rectangle(img, c1, c2, color, -1, cv2.LINE_AA)  # filled
        cv2.putText(
            img,
            label,
            (c1[0], c1[1] - 2),
            0,
            tl / 3,
            [225, 255, 255],
            thickness=tf,
            lineType=cv2.LINE_AA,
        )


class YoLov5TRT(object):
    """
    description: A YOLOv5 class that warps TensorRT ops, preprocess and postprocess ops.
    """

    def __init__(self, engine_file_path):
        # Create a Context on this device,
        self.ctx = cuda.Device(0).make_context()
        stream = cuda.Stream()
        TRT_LOGGER = trt.Logger(trt.Logger.INFO)
        runtime = trt.Runtime(TRT_LOGGER)

        # Deserialize the engine from file
        with open(engine_file_path, "rb") as f:
            engine = runtime.deserialize_cuda_engine(f.read())
        context = engine.create_execution_context()

        host_inputs = []
        cuda_inputs = []
        host_outputs = []
        cuda_outputs = []
        bindings = []

        for binding in engine:
            print('bingding:', binding, engine.get_binding_shape(binding))
            size = trt.volume(engine.get_binding_shape(binding)) * engine.max_batch_size
            dtype = trt.nptype(engine.get_binding_dtype(binding))
            # Allocate host and device buffers
            host_mem = cuda.pagelocked_empty(size, dtype)
            cuda_mem = cuda.mem_alloc(host_mem.nbytes)
            # Append the device buffer to device bindings.
            bindings.append(int(cuda_mem))
            # Append to the appropriate list.
            if engine.binding_is_input(binding):
                self.input_w = engine.get_binding_shape(binding)[-1]
                self.input_h = engine.get_binding_shape(binding)[-2]
                host_inputs.append(host_mem)
                cuda_inputs.append(cuda_mem)
            else:
                host_outputs.append(host_mem)
                cuda_outputs.append(cuda_mem)
        # Store
        self.stream = stream
        self.context = context
        self.engine = engine
        self.host_inputs = host_inputs
        self.cuda_inputs = cuda_inputs
        self.host_outputs = host_outputs
        self.cuda_outputs = cuda_outputs
        self.bindings = bindings
        self.batch_size = engine.max_batch_size

        # Data length
        self.det_output_length  = host_outputs[0].shape[0]
        self.mask_output_length = host_outputs[1].shape[0]
        self.seg_w = int(self.input_w / 4)
        self.seg_h = int(self.input_h / 4)
        self.seg_c = int(self.mask_output_length / (self.seg_w * self.seg_w))
        self.det_row_output_length = self.seg_c + 6
        
        # Draw mask
        self.colors_obj = Colors()

    def infer(self, raw_image_generator):
        t1 = time.time()
        threading.Thread.__init__(self)
        t2 = time.time()
        print(f'Line 1: {t2-t1}')
        
        # Make self the active context, pushing it on top of the context stack.
        t1 = time.time()
        self.ctx.push()
        t2 = time.time()
        print(f'Line 2: {t2-t1}')
        
        # Restore
        t1 = time.time()
        stream = self.stream
        t2 = time.time()
        print(f'Line 3: {t2-t1}')
        
        t1 = time.time()
        context = self.context
        t2 = time.time()
        print(f'Line 4: {t2-t1}')
        
        t1 = time.time()
        engine = self.engine
        t2 = time.time()
        print(f'Line 5: {t2-t1}')
        
        t1 = time.time()
        host_inputs = self.host_inputs
        t2 = time.time()
        print(f'Line 6: {t2-t1}')
        
        t1 = time.time()
        cuda_inputs = self.cuda_inputs
        t2 = time.time()
        print(f'Line 7: {t2-t1}')
        
        t1 = time.time()
        host_outputs = self.host_outputs
        t2 = time.time()
        print(f'Line 8: {t2-t1}')
        
        t1 = time.time()
        cuda_outputs = self.cuda_outputs
        t2 = time.time()
        print(f'Line 9: {t2-t1}')
        
        t1 = time.time()
        bindings = self.bindings
        t2 = time.time()
        print(f'Line 10: {t2-t1}')
        
        # Do image preprocess
        t1 = time.time() 
        batch_image_raw = []
        batch_origin_h = []
        batch_origin_w = []
        t2 = time.time()
        print(f'Line 11, 12, 13: {t2-t1}')
        
        t1 = time.time() 
        batch_input_image = np.empty(shape=[self.batch_size, 3, self.input_h, self.input_w])
        t2 = time.time()
        print(f'Line 14: {t2-t1}')
        
        t1 = time.time()
        for i, image_raw in enumerate(raw_image_generator):
            input_image, image_raw, origin_h, origin_w = self.preprocess_image(image_raw)
            batch_image_raw.append(image_raw)
            batch_origin_h.append(origin_h)
            batch_origin_w.append(origin_w)
            np.copyto(batch_input_image[i], input_image)
        t2 = time.time()
        print(f'Line 15, 16, 17, 18, 19, 20: {t2-t1}')
        
        t1 = time.time()
        batch_input_image = np.ascontiguousarray(batch_input_image)
        t2 = time.time()
        print(f'Line 21: {t2-t1}')
        
        t1 = time.time()
        # Copy input image to host buffer
        np.copyto(host_inputs[0], batch_input_image.ravel())
        t2 = time.time()
        print(f'Line 22: {t2-t1}')
       
        
        start = time.time()
        # Transfer input data  to the GPU.
        t1 = time.time()
        cuda.memcpy_htod_async(cuda_inputs[0], host_inputs[0], stream)
        t2 = time.time()
        print(f'Line 23: {t2-t1}')
        
        # Run inference.
        t1 = time.time()
        context.execute_async(batch_size=self.batch_size, bindings=bindings, stream_handle=stream.handle)
        t2 = time.time()
        print(f'Line 24: {t2-t1}')


        # Transfer predictions back from the GPU.
        t1 = time.time()
        cuda.memcpy_dtoh_async(host_outputs[0], cuda_outputs[0], stream)
        t2 = time.time()
        print(f'Line 25: {t2-t1}')
        
        t1 = time.time()
        cuda.memcpy_dtoh_async(host_outputs[1], cuda_outputs[1], stream)
        t2 = time.time()
        print(f'Line 26: {t2-t1}')
        
        # Synchronize the stream
        t1 = time.time()
        stream.synchronize()
        t2 = time.time()
        print(f'Line 27: {t2-t1}')
        end = time.time()
        
        # Remove any context from the top of the context stack, deactivating it.
        t1 = time.time()
        self.ctx.pop()
        t2 = time.time()
        print(f'Line 28: {t2-t1}')
        # Here we use the first row of output in that batch_size = 1
        
        t1 = time.time() 
        output_bbox = host_outputs[0]
        t2 = time.time()
        print(f'Line 29: {t2-t1}')
        
        t1 = time.time()
        output_proto_mask = host_outputs[1]
        t2 = time.time()
        print(f'Line 30: {t2-t1}')
        
        pp = time.time()
        # Do postprocess
        for i in range(self.batch_size): 
        
            t1 = time.time()
            result_boxes, result_scores, result_classid, result_proto_coef = self.post_process(
                output_bbox[i * self.det_output_length: (i + 1) * self.det_output_length], batch_origin_h[i], batch_origin_w[i]
            )
            t2 = time.time()
            print(f'Line 31: {t2-t1}')
            
            t1 = time.time()
            if result_proto_coef.shape[0] == 0:
                continue
            t2 = time.time()
            print(f'Line 32, 33: {t2-t1}')
            
            t1 = time.time()
            result_masks = self.process_mask(output_proto_mask, result_proto_coef, result_boxes, batch_origin_h[i], batch_origin_w[i])
            t2 = time.time()
            print(f'Line 34: {t2-t1}')
            
            
            t1 = time.time()
            # Section for Road segmentation
            road_masks = [mask for mask,result_classid in zip(result_masks,result_classid) if result_classid==1]
            combined_road_mask = np.zeros((batch_origin_h[i],batch_origin_w[i]),np.uint8)
            for road_instance in road_masks:
            	imin = road_instance.min()
            	imax = road_instance.max()
            	a = (255 - 0)/(imax - imin)
            	b = 255 - a * imax
            	buffer_mask = (a * road_instance + b).astype(np.uint8)
            	combined_road_mask = combined_road_mask | buffer_mask
            #Uncomment to view mask
            #cv2.imshow("Frame",combined_road_mask)
            white_image = np.ones((batch_origin_h[i],batch_origin_w[i]), dtype=np.uint8) * 255
            top_black_height = int(0.50 * batch_origin_h[i])
            white_image[0:top_black_height, :] = 0
            total = cv2.countNonZero(white_image)
            intersection_mask = white_image & combined_road_mask
            intersection = cv2.countNonZero(intersection_mask)  
            #print(f"Overlap of road: {(intersection/total)*100}")
            t2 = time.time()
            print(f'Section Road Segmentation: {t2-t1}')
            
            t1 = time.time()
            # Section for Footpath Segmentation
            footpath_masks = [mask for mask,result_classid in zip(result_masks,result_classid) if result_classid==0]
            combined_footpath_mask = np.zeros((batch_origin_h[i],batch_origin_w[i]),np.uint8)
            for footpath_instance in footpath_masks:
            	iminf = footpath_instance.min()
            	imaxf = footpath_instance.max()
            	c = (255 - 0)/(imaxf - iminf)
            	d = 255 - c * imaxf
            	bufferf_mask = (c * footpath_instance + d).astype(np.uint8)
            	combined_footpath_mask = combined_footpath_mask | bufferf_mask
            #Uncomment to view mask
            #cv2.imshow("Frame",combined_footpath_mask)
            white_imagef = np.ones((batch_origin_h[i],batch_origin_w[i]), dtype=np.uint8) * 255
            top_black_heightf = int(0.75 * batch_origin_h[i])
            left_black_widthf = int(0.25 * batch_origin_w[i])
            right_black_widthf = int(0.25 * batch_origin_w[i])
            white_imagef[0:top_black_heightf, :] = 0
            white_imagef[:,0:left_black_widthf] = 0
            white_imagef[:,-right_black_widthf] = 0
            totalf = cv2.countNonZero(white_imagef)
            intersection_maskf = white_imagef & combined_footpath_mask
            intersectionf = cv2.countNonZero(intersection_maskf)  
            #print(f"Overlap of footpath: {(intersectionf/totalf)*100}")
            t2 = time.time()
            print(f'Section Footpath Segmentation: {t2-t1}')
            
            
            t1 = time.time()
            # Draw masks on  the original image
            self.draw_mask(result_masks, colors_=[self.colors_obj(x, True) for x in result_classid],im_src=batch_image_raw[i])
            t2 = time.time()
            print(f'Line 35: {t2-t1}')

            # Draw rectangles and labels on the original image
            t1 = time.time()
            for j in range(len(result_boxes)):
                box = result_boxes[j]
                plot_one_box(
                    box,
                    batch_image_raw[i],
                    label="{}:{:.2f}".format(
                        categories[int(result_classid[j])], result_scores[j]
                    ),
                )
            t2 = time.time()
            print(f'Line 36: {t2-t1}')
            
        ppe = time.time()
        print(f'Total Post processing: {ppe-pp}')
        return batch_image_raw, end - start

    def destroy(self):
        # Remove any context from the top of the context stack, deactivating it.
        self.ctx.pop()

    def get_raw_image(self, image_path_batch):
        """
        description: Read an image from image path
        """
        for img_path in image_path_batch:
            yield cv2.imread(img_path)

    def get_raw_image_zeros(self, image_path_batch=None):
        """
        description: Ready data for warmup
        """
        for _ in range(self.batch_size):
            yield np.zeros([self.input_h, self.input_w, 3], dtype=np.uint8)

    def preprocess_image(self, raw_bgr_image):
        """
        description: Convert BGR image to RGB,
                     resize and pad it to target size, normalize to [0,1],
                     transform to NCHW format.
        param:
            input_image_path: str, image path
        return:
            image:  the processed image
            image_raw: the original image
            h: original height
            w: original width
        """
        image_raw = raw_bgr_image
        h, w, c = image_raw.shape
        image = cv2.cvtColor(image_raw, cv2.COLOR_BGR2RGB)
        # Calculate widht and height and paddings
        r_w = self.input_w / w
        r_h = self.input_h / h
        if r_h > r_w:
            tw = self.input_w
            th = int(r_w * h)
            tx1 = tx2 = 0
            ty1 = int((self.input_h - th) / 2)
            ty2 = self.input_h - th - ty1
        else:
            tw = int(r_h * w)
            th = self.input_h
            tx1 = int((self.input_w - tw) / 2)
            tx2 = self.input_w - tw - tx1
            ty1 = ty2 = 0
        # Resize the image with long side while maintaining ratio
        image = cv2.resize(image, (tw, th))
        # Pad the short side with (128,128,128)
        image = cv2.copyMakeBorder(
            image, ty1, ty2, tx1, tx2, cv2.BORDER_CONSTANT, None, (128, 128, 128)
        )
        image = image.astype(np.float32)
        # Normalize to [0,1]
        image /= 255.0
        # HWC to CHW format:
        image = np.transpose(image, [2, 0, 1])
        # CHW to NCHW format
        image = np.expand_dims(image, axis=0)
        # Convert the image to row-major order, also known as "C order":
        image = np.ascontiguousarray(image)
        return image, image_raw, h, w

    def xywh2xyxy(self, origin_h, origin_w, x):
        """
        description:    Convert nx4 boxes from [x, y, w, h] to [x1, y1, x2, y2] where xy1=top-left, xy2=bottom-right
        param:
            origin_h:   height of original image
            origin_w:   width of original image
            x:          A boxes numpy, each row is a box [center_x, center_y, w, h]
        return:
            y:          A boxes numpy, each row is a box [x1, y1, x2, y2]
        """
        y = np.zeros_like(x)
        r_w = self.input_w / origin_w
        r_h = self.input_h / origin_h
        if r_h > r_w:
            y[:, 0] = x[:, 0] - x[:, 2] / 2
            y[:, 2] = x[:, 0] + x[:, 2] / 2
            y[:, 1] = x[:, 1] - x[:, 3] / 2 - (self.input_h - r_w * origin_h) / 2
            y[:, 3] = x[:, 1] + x[:, 3] / 2 - (self.input_h - r_w * origin_h) / 2
            y /= r_w
        else:
            y[:, 0] = x[:, 0] - x[:, 2] / 2 - (self.input_w - r_h * origin_w) / 2
            y[:, 2] = x[:, 0] + x[:, 2] / 2 - (self.input_w - r_h * origin_w) / 2
            y[:, 1] = x[:, 1] - x[:, 3] / 2
            y[:, 3] = x[:, 1] + x[:, 3] / 2
            y /= r_h

        return y

    def post_process(self, output_boxes, origin_h, origin_w):
        """
        description: postprocess the prediction
        param:
            output:     A numpy likes [num_boxes, cx, cy, w, h, conf, cls_id, mask[32], cx, cy, w, h, conf, cls_id, mask[32] ...] 
            origin_h:   height of original image
            origin_w:   width of original image
        return:
            result_boxes: finally boxes, a boxes numpy, each row is a box [x1, y1, x2, y2]
            result_scores: finally scores, a numpy, each element is the score correspoing to box
            result_classid: finally classid, a numpy, each element is the classid correspoing to box
        """
        # Get the num of boxes detected
        num = int(output_boxes[0])
        # Reshape to a two dimentional ndarray
        pred = np.reshape(output_boxes[1:], (-1, self.det_row_output_length))[:num, :]
        # Do nms
        boxes = self.non_max_suppression(pred, origin_h, origin_w, conf_thres=CONF_THRESH,
                                         nms_thres=IOU_THRESHOLD)
        result_boxes = boxes[:, :4] if len(boxes) else np.array([])
        result_scores = boxes[:, 4] if len(boxes) else np.array([])
        result_classid = boxes[:, 5] if len(boxes) else np.array([])
        result_proto_coef = boxes[:, 6:] if len(boxes) else np.array([])
        return result_boxes, result_scores, result_classid, result_proto_coef

    def bbox_iou(self, box1, box2, x1y1x2y2=True):
        """
        description: compute the IoU of two bounding boxes
        param:
            box1: A box coordinate (can be (x1, y1, x2, y2) or (x, y, w, h))
            box2: A box coordinate (can be (x1, y1, x2, y2) or (x, y, w, h))            
            x1y1x2y2: select the coordinate format
        return:
            iou: computed iou
        """
        if not x1y1x2y2:
            # Transform from center and width to exact coordinates
            b1_x1, b1_x2 = box1[:, 0] - box1[:, 2] / 2, box1[:, 0] + box1[:, 2] / 2
            b1_y1, b1_y2 = box1[:, 1] - box1[:, 3] / 2, box1[:, 1] + box1[:, 3] / 2
            b2_x1, b2_x2 = box2[:, 0] - box2[:, 2] / 2, box2[:, 0] + box2[:, 2] / 2
            b2_y1, b2_y2 = box2[:, 1] - box2[:, 3] / 2, box2[:, 1] + box2[:, 3] / 2
        else:
            # Get the coordinates of bounding boxes
            b1_x1, b1_y1, b1_x2, b1_y2 = box1[:, 0], box1[:, 1], box1[:, 2], box1[:, 3]
            b2_x1, b2_y1, b2_x2, b2_y2 = box2[:, 0], box2[:, 1], box2[:, 2], box2[:, 3]

        # Get the coordinates of the intersection rectangle
        inter_rect_x1 = np.maximum(b1_x1, b2_x1)
        inter_rect_y1 = np.maximum(b1_y1, b2_y1)
        inter_rect_x2 = np.minimum(b1_x2, b2_x2)
        inter_rect_y2 = np.minimum(b1_y2, b2_y2)
        # Intersection area
        inter_area = np.clip(inter_rect_x2 - inter_rect_x1 + 1, 0, None) * \
                     np.clip(inter_rect_y2 - inter_rect_y1 + 1, 0, None)
        # Union Area
        b1_area = (b1_x2 - b1_x1 + 1) * (b1_y2 - b1_y1 + 1)
        b2_area = (b2_x2 - b2_x1 + 1) * (b2_y2 - b2_y1 + 1)

        iou = inter_area / (b1_area + b2_area - inter_area + 1e-16)

        return iou

    def non_max_suppression(self, prediction, origin_h, origin_w, conf_thres=0.5, nms_thres=0.4):
        """
        description: Removes detections with lower object confidence score than 'conf_thres' and performs
        Non-Maximum Suppression to further filter detections.
        param:
            prediction: detections, (x1, y1, x2, y2, conf, cls_id, mask coefficients[32])
            origin_h: original image height
            origin_w: original image width
            conf_thres: a confidence threshold to filter detections
            nms_thres: a iou threshold to filter detections
        return:
            boxes: output after nms with the shape (x1, y1, x2, y2, conf, cls_id)
        """
        # Get the boxes that score > CONF_THRESH
        boxes = prediction[prediction[:, 4] >= conf_thres]
        # Trandform bbox from [center_x, center_y, w, h] to [x1, y1, x2, y2]
        boxes[:, :4] = self.xywh2xyxy(origin_h, origin_w, boxes[:, :4])
        # clip the coordinates
        boxes[:, 0] = np.clip(boxes[:, 0], 0, origin_w - 1)
        boxes[:, 2] = np.clip(boxes[:, 2], 0, origin_w - 1)
        boxes[:, 1] = np.clip(boxes[:, 1], 0, origin_h - 1)
        boxes[:, 3] = np.clip(boxes[:, 3], 0, origin_h - 1)
        # Object confidence
        confs = boxes[:, 4]
        # Sort by the confs
        boxes = boxes[np.argsort(-confs)]
        # Perform non-maximum suppression
        keep_boxes = []
        while boxes.shape[0]:
            large_overlap = self.bbox_iou(np.expand_dims(boxes[0, :4], 0), boxes[:, :4]) > nms_thres
            label_match = boxes[0, 5] == boxes[:, 5]
            # Indices of boxes with lower confidence scores, large IOUs and matching labels
            invalid = large_overlap & label_match
            keep_boxes += [boxes[0]]
            boxes = boxes[~invalid]
        boxes = np.stack(keep_boxes, 0) if len(keep_boxes) else np.array([])
        return boxes

    def sigmoid(self, x):
        return 1 / (1 + np.exp(-x))

    def scale_mask(self, mask, ih, iw):
        mask = cv2.resize(mask, (self.input_w, self.input_h))
        r_w = self.input_w / (iw * 1.0)
        r_h = self.input_h / (ih * 1.0)
        if r_h > r_w:
            w = self.input_w
            h = int(r_w * ih)
            x = 0
            y = int((self.input_h - h) / 2)
        else:
            w = int(r_h * iw)
            h = self.input_h
            x = int((self.input_w - w) / 2)
            y = 0
        crop = mask[y:y+h, x:x+w]
        crop = cv2.resize(crop, (iw, ih))
        return crop


    def process_mask(self, output_proto_mask, result_proto_coef, result_boxes, ih, iw):
        """
        description: Mask pred by yolov5 instance segmentation ,
        param: 
            output_proto_mask: prototype mask e.g. (32, 160, 160) for 640x640 input
            result_proto_coef: prototype mask coefficients (n, 32), n represents n results
            result_boxes     :  
            ih: rows of original image
            iw: cols of original image
        return:
            mask_result: (n, ih, iw)
        """
        result_proto_masks = output_proto_mask.reshape(self.seg_c, self.seg_h, self.seg_w)
        c, mh, mw = result_proto_masks.shape
        masks = self.sigmoid((result_proto_coef @ result_proto_masks.astype(np.float32).reshape(c, -1))).reshape(-1, mh, mw)
        mask_result = []

        for mask, box in zip(masks, result_boxes):
            mask_s = np.zeros((ih, iw))
            crop_mask = self.scale_mask(mask, ih, iw)            
            x1 = int(box[0])
            y1 = int(box[1])
            x2 = int(box[2])
            y2 = int(box[3])
            crop = crop_mask[y1:y2, x1:x2]
            crop = np.where(crop >= 0.5, 1, 0)
            crop = crop.astype(np.uint8)
            mask_s[y1:y2, x1:x2] = crop
            mask_result.append(mask_s)

        mask_result = np.array(mask_result)
        return mask_result

    def draw_mask(self, masks, colors_, im_src, alpha=0.5):
        """
        description: Draw mask on image ,
        param: 
            masks  : result_mask
            colors_: color to draw mask
            im_src : original image
            alpha  : scale between original  image and mask
        return:
            no return
        """
        if len(masks) == 0:
            return
        masks = np.asarray(masks, dtype=np.uint8)
        masks = np.ascontiguousarray(masks.transpose(1, 2, 0))
        masks = np.asarray(masks, dtype=np.float32)
        colors_ = np.asarray(colors_, dtype=np.float32)
        s = masks.sum(2, keepdims=True).clip(0, 1)
        masks = (masks @ colors_).clip(0, 255)
        im_src[:] = masks * alpha + im_src * (1 - s * alpha)
    

class inferThread(threading.Thread):
    def __init__(self, yolov5_wrapper, image_path_batch):
        threading.Thread.__init__(self)
        self.yolov5_wrapper = yolov5_wrapper
        self.image_path_batch = image_path_batch

    def run(self):
        batch_image_raw, use_time = self.yolov5_wrapper.infer(self.yolov5_wrapper.get_raw_image(self.image_path_batch))
        for i, img_path in enumerate(self.image_path_batch):
            parent, filename = os.path.split(img_path)
            save_name = os.path.join('output', filename)
            # Save image
            cv2.imwrite(save_name, batch_image_raw[i])
        print('input->{}, time->{:.2f}ms, saving into output/'.format(self.image_path_batch, use_time * 1000))


class warmUpThread(threading.Thread):
    def __init__(self, yolov5_wrapper):
        threading.Thread.__init__(self)
        self.yolov5_wrapper = yolov5_wrapper

    def run(self):
        batch_image_raw, use_time = self.yolov5_wrapper.infer(self.yolov5_wrapper.get_raw_image_zeros())
        print('warm_up->{}, time->{:.2f}ms'.format(batch_image_raw[0].shape, use_time * 1000))


class Colors:
    def __init__(self):
        hexs = ('FF3838', 'FF9D97', 'FF701F', 'FFB21D', 'CFD231', '48F90A',
                '92CC17', '3DDB86', '1A9334', '00D4BB', '2C99A8', '00C2FF',
                '344593', '6473FF', '0018EC', '8438FF', '520085', 'CB38FF',
                'FF95C8', 'FF37C7')
        self.palette = [self.hex2rgb(f'#{c}') for c in hexs]
        self.n = len(self.palette)

    def __call__(self, i, bgr=False):
        c = self.palette[int(i) % self.n]
        return (c[2], c[1], c[0]) if bgr else c

    @staticmethod
    def hex2rgb(h):  # rgb order (PIL)
        return tuple(int(h[1 + i:1 + i + 2], 16) for i in (0, 2, 4))

if __name__ == "__main__":
    PLUGIN_LIBRARY = "yolov5/build/libmyplugins.so"
    engine_file_path = "Seg/best_seg.engine"
    if len(sys.argv) > 1:
        engine_file_path = sys.argv[1]
    if len(sys.argv) > 2:
        PLUGIN_LIBRARY = sys.argv[2]

    ctypes.CDLL(PLUGIN_LIBRARY)

    categories = ["Footpath","Road"]

    # Create an instance of the YoLov5TRT class
    instance_creation_start = time.time() 
    yolov5_wrapper = YoLov5TRT(engine_file_path)
    instance_creation_end = time.time() 
    print(f'Instance Creation time for Engine and plugin library: {instance_creation_end-instance_creation_start} ms')
    # Open a video capture object
    video_path = "videos/Input_fp_1.mp4"  # Replace with your video file path
    cap = cv2.VideoCapture(video_path)

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # Resize the frame if needed
            #frame = cv2.resize(frame, (width, height))
            total_time_start = time.time() 
            # Perform inference on the current frame
            result_image, use_time = yolov5_wrapper.infer([frame])
            total_time_end = time.time() 
            print(f'Complete execution time for Engine and plugin library: {total_time_end-total_time_start } ms')
            # Display or save the processed frame
            cv2.imshow("Processed Frame", result_image[0])

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()
        yolov5_wrapper.destroy()
