
import {
  FaceLandmarker,
  FilesetResolver
} from "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14";

const video = document.querySelector("#webcam");
const status = document.querySelector("#status");

let faceLandmarker;
let closedSince = null;
let lastBlinkTime = 0;
let selectedElement = null;

const BLINK_THRESHOLD = 0.65;
const MIN_BLINK_DURATION = 500;
const MAX_BLINK_DURATION = 1200;
const CLICK_COOLDOWN = 900;
const gazeDot = document.querySelector("#gazeDot");

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}


function updateGaze(landmarks) {
  if (!landmarks || landmarks.length < 478) {
    return;
  }

  const gazeDot = document.querySelector("#gazeDot");

  const leftIris = landmarks[468];
  const rightIris = landmarks[473];

  const leftOuter = landmarks[33];
  const leftInner = landmarks[133];

  const rightOuter = landmarks[362];
  const rightInner = landmarks[263];

  const leftTop = landmarks[159];
  const leftBottom = landmarks[145];

  const rightTop = landmarks[386];
  const rightBottom = landmarks[374];

  const leftWidth = Math.abs(leftOuter.x - leftInner.x);
  const rightWidth = Math.abs(rightOuter.x - rightInner.x);

  const leftHeight = Math.abs(leftTop.y - leftBottom.y);
  const rightHeight = Math.abs(rightTop.y - rightBottom.y);
  
  if (
    leftWidth < 0.001 ||
    rightWidth < 0.001 ||
    leftHeight < 0.001 ||
    rightHeight < 0.001
  ) {
    return;
  }
  

  const horizontal =
    (
      (leftIris.x - Math.min(leftOuter.x, leftInner.x)) / leftWidth +
      (rightIris.x - Math.min(rightOuter.x, rightInner.x)) / rightWidth
    ) / 2;

  const vertical =
    (
      (leftIris.y - leftTop.y) / (leftBottom.y - leftTop.y) +
      (rightIris.y - rightTop.y) / (rightBottom.y - rightTop.y)
    ) / 2;

  const x = Math.max(2, Math.min(98, 100 - horizontal * 100));
  const y = Math.max(2, Math.min(98, 100 - vertical * 100));

  gazeDot.style.left = x + "%";
  gazeDot.style.top = y + "%";
  gazeDot.style.display = "block";

  

}


// Initialize MediaPipe
async function initialize() {
  const vision = await FilesetResolver.forVisionTasks(
    "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm"
  );

  faceLandmarker = await FaceLandmarker.createFromOptions(
    vision,
    {
      baseOptions: {
        modelAssetPath: "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
        delegate: "GPU"
      },
      runningMode: "VIDEO",
      numFaces: 1,
      outputFaceBlendshapes: true
    }
  );
}

// Start camera
async function startCamera() {
  const stream = await navigator.mediaDevices.getUserMedia({
    video: true,
    audio: false
  });

  video.srcObject = stream;

  await new Promise(resolve => {
    video.onloadedmetadata = resolve;
  });

  await video.play();
}
// Detect blinks

function processBlink(result) {

  if (!result.faceLandmarks?.length) {
    closedSince = null;
    gazeDot.style.display = "none";
    status.textContent = "No face detected";
    return;
  }

  // Get face landmarks
  const landmarks = result.faceLandmarks[0];

  // Update visible gaze indicator
  gazeDot.style.display = "block";
  updateGaze(landmarks);

  // Existing blink detection
  if (!result.faceBlendshapes?.length) {
    closedSince = null;
    status.textContent = "Face detected | Tracking eyes...";
    return;
  }

  const categories = result.faceBlendshapes[0].categories;

  const scores = Object.fromEntries(
    categories.map(item => [
      item.categoryName,
      item.score
    ])
  );

  const left = scores.eyeBlinkLeft ?? 0;
  const right = scores.eyeBlinkRight ?? 0;

  const bothClosed =
    left > BLINK_THRESHOLD &&
    right > BLINK_THRESHOLD;

  const now = performance.now();

  if (bothClosed) {
    if (closedSince === null) {
      closedSince = now;
    }

    status.textContent = "Eyes closed...";
    return;
  }

  if (closedSince !== null) {
    const duration = now - closedSince;
    closedSince = null;

    if (
      duration >= MIN_BLINK_DURATION &&
      duration <= MAX_BLINK_DURATION &&
      now - lastBlinkTime > CLICK_COOLDOWN
    ) {
      lastBlinkTime = now;
      activateSelection();
    }
  }

  status.textContent = "Face detected | Gaze tracking active";
}


// Activate selected button
function activateSelection() {
  if (selectedElement) {
    selectedElement.click();
    status.textContent = "Blink click detected!";
  }
}

// Tracking loop
function trackingLoop() {
  if (video.readyState >= 2) {
    const result = faceLandmarker.detectForVideo(
      video,
      performance.now()
    );

    processBlink(result);
  }

  requestAnimationFrame(trackingLoop);
}

// Start application

async function startApp() {
  try {
    status.textContent = "1. Loading MediaPipe...";

    console.log("Loading MediaPipe...");

    const vision = await FilesetResolver.forVisionTasks(
      "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm"
    );

    status.textContent = "2. Loading face model...";

    console.log("Loading face model...");

    faceLandmarker = await FaceLandmarker.createFromOptions(
      vision,
      {
        baseOptions: {
          modelAssetPath:
            "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
          delegate: "CPU"
        },
        runningMode: "VIDEO",
        numFaces: 1,
        outputFaceBlendshapes: true
      }
    );

    status.textContent = "3. Starting webcam...";

    console.log("Starting webcam...");

    await startCamera();

    selectElement(document.querySelector("#button1"));

    status.textContent = "4. Starting eye tracking...";

    console.log("Starting tracking...");

    trackingLoop();

    status.textContent = "Eye tracking started!";

  } catch (error) {
    console.error("INITIALIZATION ERROR:", error);

    status.textContent =
      "Initialization failed: " + error.message;
  }
}




function selectElement(element) {
  if (!element) return;

  if (selectedElement) {
    selectedElement.classList.remove("selected");
  }

  selectedElement = element;
  selectedElement.classList.add("selected");
}

startApp();
