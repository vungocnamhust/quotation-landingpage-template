const docWidth = document.documentElement.clientWidth;
[].forEach.call(document.querySelectorAll('*'), function(el) {
  if (el.scrollWidth > docWidth) {
    console.log(el.tagName + '.' + el.className + ' width: ' + el.scrollWidth);
  }
});
