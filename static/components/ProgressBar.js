class ProgressBar extends HTMLElement {
  static EMITS = {
    MOUNTED: "mounted",
    FINISH: "finished",
  };
  static ATTRS = {
    PROGRESS: "progress",
  };

  constructor() {
    super();
    this.rendered = false;
  }

  get progress() {
    return this.getAttribute(ProgressBar.ATTRS.PROGRESS);
  }

  set progress(newValue) {
    if (isNaN(Number(newValue))) {
      throw Error(
        "значение должно быть числом или строкой, представляющей число"
      );
    }
    this.setAttribute(ProgressBar.ATTRS.PROGRESS, newValue);
  }

  render() {
    const progressValue = this.getAttribute("progress");
    this.innerHTML = `<div style="background: linear-gradient(90deg, white ${progressValue}%, transparent 0%); height: 30px;"></div>`;
  }

  emit(type, config = {}) {
    const { bubbles = false, cancelable = true, detail = "" } = config;
    const event = new CustomEvent(type, {
      bubbles,
      detail,
      cancelable,
    });
    return this.dispatchEvent(event);
  }

  static get observedAttributes() {
    return [this.ATTRS.PROGRESS];
  }

  connectedCallback() {
    if (!this.rendered) {
      this.render();
      this.rendered = true;
      setTimeout(() => {
        this.emit(ProgressBar.EMITS.MOUNTED, {
          detail: "progress bar mount event",
        });
      }, 0);
    }
  }

  attributeChangedCallback() {
    this.render();
    if (this.progress === '100') {
      this.emit(ProgressBar.EMITS.FINISH, { detail: "progress bar finished" });
    }
  }
}

export default ProgressBar;
