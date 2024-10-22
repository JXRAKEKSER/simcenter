const BASE_URL = "http://localhost:8000/sse/room";
const roomNumber = parseParams();
const audio = document.querySelector('audio');

function parseParams() {
  const [, roomNumberWithSlash] = location.pathname.split(
    "/accreditation-voise/"
  );
  return roomNumberWithSlash.slice(0, -1);
}

const audioMap = {
  START: "/static/voise/begin.mp3",
  READ_TASK: "/static/voise/read_task.mp3",
  BEFORE_END: "/static/voise/left_2_minutes.mp3",
  END: "/static/voise/end.mp3",
};

function init() {
  const source = new EventSource(`${BASE_URL}/${roomNumber}`);
  source.addEventListener("error", (event) => {
    console.log({ error: event });
  });

  source.addEventListener("stream_event", (event) => {
    const currentSrc = audioMap[event.data];
    if (!currentSrc) {
        return;
    }
    audio.src = currentSrc;
    audio.play();
  });
}

init();
