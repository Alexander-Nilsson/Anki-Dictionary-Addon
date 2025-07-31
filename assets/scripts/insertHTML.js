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

  if (action === "overwrite") {
    editableField.innerHTML = newHTML;
  } else if (action === "add") {
    if (editableField.innerHTML === "<br>" || editableField.innerHTML.trim() === "") {
      editableField.innerHTML = newHTML;
    } else {
      editableField.innerHTML = editableField.innerHTML + "<br><br>" + newHTML;
    }
  } else if (action === "no") {
    if (editableField.innerHTML === "<br>" || editableField.innerHTML.trim() === "") {
      editableField.innerHTML = newHTML;
    }
  }

  pycmd("key" + ":" + parseInt(ord) + ":" + currentNoteId + ":" + editableField.innerHTML);
}

try {
  insertHTML("%s", "%s", "%s", "%s");
} catch (e) {
  console.error("Error in insertHTML:", e);
}