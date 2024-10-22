import voiseApi from "./api.js";

const STAGES = {
  START: "START",
  READ_TASK: "READ_TASK",
  BEFORE_END: "BEFORE_END",
  END: "END",
};

class ManageAccreditation {
  delay = 30_000;

  static STAGES = STAGES;

  constructor(roomNumber) {
    this.roomNumber = roomNumber;
    this.stage = null;
    this.generator = this.stageGenerator();
  }

  start() {
    this.#nextStage();
    voiseApi.startSession(this.roomNumber);
  }

  update() {
    this.#nextStage();
    console.log(this.currentStage)
    voiseApi.patchSession(this.roomNumber, this.currentStage)
  }

  *stageGenerator() {
    yield ManageAccreditation.STAGES.START;
    yield ManageAccreditation.STAGES.READ_TASK;
    yield ManageAccreditation.STAGES.BEFORE_END;
    yield ManageAccreditation.STAGES.END;
  }

  #nextStage() {
    this.stage = this.generator.next();
  }

  get currentStage() {
    return this.stage.value;
  }
}

export default ManageAccreditation;
