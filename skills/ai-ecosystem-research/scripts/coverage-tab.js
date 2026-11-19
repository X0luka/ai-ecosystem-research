(() => {
  const tabs = document.querySelector('#tabs');
  const panel = document.querySelector('#coverage-panel');
  const content = ['#intro', '.tools', '#list', '.pager'].map(selector => document.querySelector(selector));
  tabs.after(panel);
  const button = document.createElement('button');
  button.textContent = '覆盖审计';
  function attach() {
    if (!tabs.contains(button)) {
      tabs.append(button);
      panel.hidden = true;
      button.classList.remove('active');
      content.forEach(node => node.style.removeProperty('display'));
    }
  }
  button.onclick = () => {
    tabs.querySelectorAll('button').forEach(node => node.classList.toggle('active', node === button));
    panel.hidden = false;
    content.forEach(node => node.style.display = 'none');
  };
  attach();
  new MutationObserver(attach).observe(tabs, {childList: true});
})();
