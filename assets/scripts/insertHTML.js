function insertHTML(newHTML, ord, action, currentNoteId) {
  const fieldContainers = document.querySelectorAll(".field-container");
  if (!fieldContainers || fieldContainers.length <= ord) {
    console.error("Field container not found for ord:", ord);
    return;
  }
  const fieldContainer = fieldContainers[ord];
  const editableField = fieldContainer.querySelector(".rich-text-editable");
  if (!editableField) {
    console.error("Editable field not found in container:", fieldContainer);
    return;
  }

  // Anki 25.09+ renders the actual rich-text editor inside an open shadow
  // root. Older versions kept the editable element in the light DOM.
  const target = editableField.shadowRoot
    ? editableField.shadowRoot.querySelector(
        'anki-editable, [contenteditable="true"]',
      ) || editableField
    : editableField;

  const currentHTML = target.innerHTML;
  const isEmpty = currentHTML === "<br>" || currentHTML.trim() === "";
  if (action === "overwrite") {
    target.innerHTML = newHTML;
  } else if (action === "add") {
    target.innerHTML = isEmpty
      ? newHTML
      : currentHTML + "<br><br>" + newHTML;
  } else if (action === "no") {
    if (!isEmpty) {
      return;
    }
    target.innerHTML = newHTML;
  }

  // Let the editor's own input handlers notice the change, then sync the
  // note model through Anki's editor bridge.
  target.dispatchEvent(new InputEvent("input", { bubbles: true }));
  pycmd("key:" + parseInt(ord) + ":" + currentNoteId + ":" + target.innerHTML);
}

try {
  insertHTML(%s, %s, %s, %s);
} catch (e) {
  console.error("Error in insertHTML:", e);
}
