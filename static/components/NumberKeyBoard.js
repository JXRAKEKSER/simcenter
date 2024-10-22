class NumberKeyboard extends HTMLElement {
  static EVENTS = {
    KEY_CLICKED: "key-clicked",
  };

  constructor() {
    super();
    this.rendered = false;
    this.listener = null;
  }

  render() {
    const templateContent = document.getElementById("keyboard").content;
    const clonedKeyBoardTemplate = templateContent.cloneNode(true);
    this.appendChild(clonedKeyBoardTemplate);
    this.listener = (event) => {
      this.keyBoardClickListener(event);
    };
    this.querySelector('div').addEventListener("click", this.listener);
  }

  /**
   *
   * @param {MouseEvent} event
   */
  keyBoardClickListener(event) {
    const { target } = event;
    const keyValue = target.dataset.value;
    if (!keyValue) {
      return;
    }
    
    this.emit(NumberKeyboard.EVENTS.KEY_CLICKED, { detail: { keyValue } });
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

  connectedCallback() {
    if (!this.rendered) {
      this.render();
      this.rendered = true;
    }
  }
}

export default NumberKeyboard;
