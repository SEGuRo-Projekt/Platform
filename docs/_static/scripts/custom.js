function replaceTextNodes(node, oldText, newText) {
  node.childNodes.forEach(function (el) {
    if (el.nodeType === 3) {
      el.nodeValue = el.nodeValue.replace(oldText, newText);
    } else {
      replaceTextNodes(el, oldText, newText);
    }
  });
}

// Fix-up domain of links in case we are not on localhost
oldText = "localhost";
newText = window.location.hostname;

for (let link of document.getElementsByTagName('a')) {
  if (link.hostname.endsWith("localhost")) {
    link.hostname = link.hostname.replace(oldText, newText);

    replaceTextNodes(link, oldText, newText);

    console.log(link);
  }
}
