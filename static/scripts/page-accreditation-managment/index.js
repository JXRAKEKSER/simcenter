import ManageAccreditation from "./manage.accreditation.js";

const startButton = document.querySelector("#start-button");
const updateButton = document.querySelector('#update-button');

let roomNumber = null;

function parseParams() {
  const [, roomNumberWithSlash] = location.pathname.split(
    "/accreditation-managment/"
  );
  return roomNumberWithSlash.slice(0, -1);
}

function createHandlers() {
  const roomNumber = parseParams();
  const manageAccred = new ManageAccreditation(roomNumber);

  function handleStart() {
    manageAccred.start();
  }

  function handleUpdate() {
    manageAccred.update();
  }

  return { handleStart, handleUpdate };
}

function setListeners() {
  const { handleStart, handleUpdate } = createHandlers();
  if (!startButton) {
    return;
  }
  startButton.addEventListener("click", handleStart);
  updateButton.addEventListener('click', handleUpdate);
}

function init() {
  setListeners();
}

init();
