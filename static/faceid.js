
const video = document.getElementById('video');



Promise.all([
  faceapi.nets.faceRecognitionNet.loadFromUri('../static/models'),
  faceapi.nets.tinyFaceDetector.loadFromUri('../static/models'),
  faceapi.nets.faceLandmark68Net.loadFromUri('../static/models'),
  faceapi.nets.faceRecognitionNet.loadFromUri('../static/models'),
  faceapi.nets.ssdMobilenetv1.loadFromUri('../static/models'),
]).then(startVideo);
const options = new faceapi.SsdMobilenetv1Options({ minConfidence: 0.9 });

function startVideo() {
  navigator.getUserMedia(
    { video: {} },
    stream => video.srcObject = stream,
    err => console.error(err)
  )
}
var ph = 0
video.addEventListener('play', () => {
  const canvas = faceapi.createCanvasFromMedia(video);
  document.body.append(canvas);
  const displaySize = { width: video.width, height: video.height };
  faceapi.matchDimensions(canvas, displaySize);

  let labeledFaceDescriptors
  (async () => {
    labeledFaceDescriptors = await loadLabeledImages();
  })();
setInterval(async () => {
    const detections = await faceapi.detectAllFaces(video).withFaceLandmarks().withFaceDescriptors();
    const resizedDetections = faceapi.resizeResults(detections, displaySize);
    canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height);

    if (labeledFaceDescriptors) {
      const faceMatcher = new faceapi.FaceMatcher(labeledFaceDescriptors, 0.50);
      const results = resizedDetections.map(d => faceMatcher.findBestMatch(d.descriptor));
      results.forEach((result, i) => {
        const box = resizedDetections[i].detection.box;
        const drawBox = new faceapi.draw.DrawBox(box, { label: result.toString() });
        drawBox.draw(canvas);
        console.log(result.label);
        if (result.label=='Прошел' && ph == 0){
        window.location = '/printf/'+ myVar;
        ph ++;
        }
      });
    }

  }, 200);
});

function loadLabeledImages() {
  const labels = ['Прошел']
  return Promise.all(
    labels.map(async label => {
      const descriptions = [];
      for (let i = 0; i <= 1; i++){
        const img = await faceapi.fetchImage("../static/photo/"+ myVar+"/"+ files[i]);
        const detections = await faceapi.detectSingleFace(img).withFaceLandmarks().withFaceDescriptor();
        descriptions.push(detections.descriptor);
      }
      return new faceapi.LabeledFaceDescriptors(label, descriptions);
    }));
  
}