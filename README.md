# Chest X-Ray Abnormality Detection System: Technical Architecture & Documentation

## SECTION 1 — Project Overview

*   **Brief description of the system:** An AI-powered medical imaging web application designed to automatically detect and localize 14 distinct types of abnormalities in chest X-ray images using deep learning.
*   **Primary objective:** To assist medical professionals, particularly radiologists, by highlighting potential pathological areas on chest X-rays, thus expediting the diagnostic process and reducing the likelihood of critical findings being missed during high-volume screening.
*   **Target users:** Radiologists, clinicians, and medical researchers seeking a preliminary diagnostic screening tool to act as a "second pair of eyes" before conducting their own detailed expert analysis.
*   **Key capabilities:**
    *   Image upload interface supporting single or batch chest X-ray image ingestion.
    *   High-speed object detection inference (YOLO-based) routing against the X-ray data.
    *   Interactive dashboard displaying bounding boxes, confidence ratings, and abnormality classification types.
    *   RESTful API backend for decoupling object detection models and frontend user interfaces, enabling potential integrations.

## SECTION 2 — Model Architecture Analysis

| Component | Model Name | Purpose | Input | Output | Why Chosen |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Object Detection Model | YOLO11m (Ultralytics) | Detect and localize 14 classes of chest X-ray abnormalities | Chest X-ray image (resized to 640x640) | Bounding box coordinates (xyxy), class ID, and confidence score | State-of-the-art speed/accuracy trade-off, single-stage detection; ideal balance (m) of latency/hardware needs vs. precision; seamless integration with PyTorch. |

*   **Role of the model:** The primary analytical engine processing the X-ray images, parsing them through a convolutional neural network architecture and outputting spatial predictions corresponding to specific anatomical aberrations with associated probability distributions.
*   **Advantages over alternatives:** Compared to two-stage detectors (e.g., Faster R-CNN) or pure transformer setups (DeTR), the YOLO11m provides exceptionally fast inference without sacrificing the spatial accuracy required for recognizing small lesions and subtle pleural abnormalities, essential for real-time web application interactivity.
*   **Limitations:** Highly dependent on the quality and diverse structural distribution of the training dataset. Like all object detection models, it may struggle with highly overlapping conditions or exceptionally subtle infiltrates that even human specialists find difficult to discern without complementary clinical context.

## SECTION 3 — Training Analysis

### 3.1 Dataset
*   **Dataset name:** [VinDr-CXR] (implied based on 14 class datasets)
*   **Number of classes:** 14 (Aortic enlargement, Atelectasis, Calcification, Cardiomegaly, Consolidation, ILD, Infiltration, Lung Opacity, Nodule/Mass, Other lesion, Pleural effusion, Pleural thickening, Pneumothorax, Pulmonary fibrosis).
*   **Annotation type:** Bounding box (YOLO format)
*   **Train/val/test split:** Implied standard allocation enabling iterative training run tracking, hyperparameter tuning, model performance validation logic metrics testing.

### 3.2 Training Configuration
*   **Framework used:** Ultralytics YOLO (PyTorch backend)
*   **Loss functions:** CIoU (Complete Intersection over Union) for Box, Classification loss and Bounding box Regression loss (via DFL).
*   **Optimizer:** AdamW
*   **Image size:** 640x640 input resolution
*   **Epochs:** 100 (with early stopping patience of 50 epochs)
*   **Learning Rate Strategy:** Initial LR = 0.01 (or 0.002 for fine-tuning), weight decay = 0.0005, and 3 epochs of warmup.
*   **Hardware used:** Designed for CUDA-enabled GPUs to allow for batch processing matrix parallelism (implied usage), with CPU fallback mechanism integrated into the inference code.
*   **Augmentation Techniques:** Standard pipeline configured for medical imaging constraints, including mosaic augmentation (0.5), mixup (0.1), translation/scaling, flipping, and HSV tuning.

### 3.3 Performance Metrics
*   **mAP50:** 0.336 (33.6%)
*   **mAP50-95:** 0.168 (16.8%)
*   **Precision:** 0.392 (39.2%)
*   **Recall:** 0.356 (35.6%)
*   **Training challenges:** Medical imaging annotations frequently suffer from high inter-reader variability, making bounding box intersections notoriously inconsistent between different human radiologist labels.
*   **Overfitting handling:** Managed via rigorous early stopping algorithms (patience=50), aggressive synthetic dataset augmentation (Mixup, Mosaic interpolation), and regularization integrated within the AdamW optimization sequence (weight decay=0.0005).

## SECTION 4 — Backend Architecture

*   **Backend framework:** FastAPI (Python 3.10+). Due to its high performance, asynchronous request-handling capability, and auto-generated API schema documentation.
*   **Model serving method:** Model weights instantiated into system memory via the `YOLO()` object model constructor (`YOLO(MODEL_PATH)`) at application launch. Inference logic runs inline within the request processing execution context.
*   **API endpoints:**
    *   `GET /`: API entry point and version ping.
    *   `GET /health`: Diagnostic status of API targeting device schema specs and model loaded availability.
    *   `GET /model_info`: Retrieves model parameters/architecture summary, returning public specs JSON.
    *   `POST /predict`: Handles single image multipart upload. Returns processed inference run timestamps, base 64 output UI counter metrics, and array of structured JSON dict coordinates.
    *   `POST /batch_predict`: Orchestrates iterative looping over array of file payload schemas for bulk image inference testing.
*   **Database:** (No explicit DB connection exists in the current application logic snippets given — the application handles stateless transformations processing and returning immediate results).
*   **Scalability considerations:** Because inference holds the GPU memory context, highly concurrent loads will cause request queuing delays. True production scale would necessitate decoupling the AI execution into a task queue backend (e.g., Celery/Redis) or moving inference to a dedicated orchestration grid (e.g., Triton Inference Server).

**Request Flow Diagram**

```text
Client
[Upload IMG] (Multipart form-data) -> [FastAPI POST /predict]

           | (Bytes conversion)

     [Pillow Image Object (RGB)]

           | (Inference execution via Ultralytics)
   
[Ultralytics Output Tensors -> cls, conf, xyxy] -> [YOLO11m prediction engine module -> GPU/CPU]
           
           | (Parsing logic)

[Prediction Parser algorithm logic -> dict array] -> [JSON Payload -> Client UI]
```

## SECTION 5 — Frontend Architecture

*   **Frontend framework:** React.js / Vite build tool
*   **Major UI components:**
    *   `Navbar`: Persistent site navigation and branding component.
    *   `UploadZone / ImageUploader`: Drag-and-drop file interface mapping user inputs to the system state.
    *   `ResultsDashboard / ImageViewer`: Dedicated canvas container intelligently rendering bounding boxes, class labels, and confidence overlays corresponding precisely over the processed X-ray image dimensions.
*   **Frontend communication with backend:** Uses asynchronous fetch API calls directed to the running FastAPI localhost port (e.g., `http://127.0.0.1:8000/predict`) handling POST multipart form-data requests with robust error catching.
*   **State management approach:** React Hooks (`useState`, `useEffect`) track the complex application state lifecycles: tracking file selection, upload indexing sequences, HTTP processing flags, and JSON detection payload objects needed for rendering the underlying DOM layout nodes.
*   **User workflow:**
    1.  User accesses graphical web portal.
    2.  Selects local X-ray image binary via drag-and-drop region mechanism.
    3.  Clicks "Detect" triggering async network payload serialization.
    4.  Waits via processing sequence UI placeholder.
    5.  The API responds with JSON; UI transforms the state to a summary display rendering bounding boxes, confidence ratings, and classified category overlays that precisely fit to original uploaded x-ray image dimensions.

## SECTION 6 — End-to-End System Flow
1.  **User Input:** Client application mounts file binary locally and transmits an HTTP POST request to API.
2.  **Preprocessing:** FastAPI receives file byte stream, buffers it in memory context, and coerces the data type using PIL library to convert to an RGB 3-channel structure expected by the backend inference module.
3.  **Model Inference:** The image object is passed to the loaded YOLO11m engine. The target framework performs complex matrix operations utilizing available system processing cores (ideally GPU) yielding model predictions.
4.  **Postprocessing:** Tensor outputs bounding box coordinates, class indices, and confidence probabilities are parsed. A custom utility function extracts, normalizes, and filters these matrices iterating based on confidence threshold heuristics.
5.  **Response Return:** The final structured data object (dict array) transforms to a JSON dictionary string and transmits back through the network framework to the client requesting endpoint connection.

## SECTION 7 — Design Rationale
*   **Why this specific AI model (YOLO11m)?** The balance of inference speed handling and anatomical structural localization accuracy required in a live application. Two-stage detection (R-CNN algorithms) are too computationally intensive leading to poor web usability loading times, especially over many diagnostic workflows. The 'm' (medium) parameter variant balances reasonable throughput efficiency across mid-range GPU hardware profiles without heavily compromising true positive detection identification performance against subtle lesion features.
*   **Why this backend stack (FastAPI)?** Modern Python applications prioritizing speed benefit massively from FastAPI’s asynchronous underlying architectures (Starlette framework) for IO bound web operations like image uploads. Out of the box, automatic Swagger UI interactive documentation validation with Pydantic typing provides an exceptional developer iteration curve allowing the building of object inference logic endpoints cleanly and effectively over traditional Flask application patterns.
*   **Frontend choices and UI:**
    *   Vite was adopted over Create React App because its 'Hot Module Replacement' (HMR) technology substantially accelerates bundle build and update rendering testing significantly expediting rapid React application building processes.
    *   React `useState` combined with raw Fetch UI calls effectively minimizes application file weight sizes vs heavier complex component library imports like Redux/Axios, ensuring browser rendering operations remain smooth and predictable without needing to scale complexity to larger architecture state trees unnecessarily.

## SECTION 8 — Limitations and Future Improvements
**Known limitations:**
*   **Training Constraints/Dataset Bias:** Deep learning model is heavily localized/constrained strictly to generalized VinDr datasets structure performance. The model may generate artifact falsifications when presented with external hardware scanner variance (e.g. overexposed scans, prominent clothing artifacts, pacemaker implants not adequately represented in training dataset matrices).
*   **Monolithic API Scaling:** The current architecture deeply couples the application server processes taking direct CPU/GPU cycle hits with API endpoint request routing, presenting a significant bottleneck capping concurrent traffic operations.
*   **Class Imbalance:** The inherent data structure mapping within medical object sets tends towards overwhelming class bias (Aortic enlargement 24,000 class objects vs Pulmonary fibrosis 400).

**Future improvements:**
*   **Asynchronous Task Queuing:** Architecting requests queuing schemas utilizing dedicated messaging brokers/workers logic (RabbitMQ/Celery or Redis backends). This approach segregates network routing wait times separating heavy ML inference computation into isolated container blocks.
*   **Advanced Preprocessing via DICOM:** Standardizing pipeline processes to natively accept multi-layered and metadata-rich uncompressed DICOM datasets over the basic array-lossy formats like JPEG, which inherently introduces compression artifact biases that degrade bounding box spatial reliability.
*   **Transfer Learning Iteration Cycle:** Establishing database infrastructure logic allowing medical professionals using the system to review bounding outputs internally mapping flagged model false-positives/negatives back into dataset pipelines pushing active-learning mechanisms towards more precise diagnostic benchmarks iteratively.
