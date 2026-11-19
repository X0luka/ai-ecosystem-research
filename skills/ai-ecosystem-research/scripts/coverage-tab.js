(() => {
  const tabs = document.querySelector('#tabs');
  const panel = document.querySelector('#coverage-panel');
  const content = ['#intro', '.tools', '#list', '.pager'].map(selector => document.querySelector(selector)).filter(Boolean);
  tabs.after(panel);
  const home = document.querySelector('#coverage-home');
  const anchor = document.querySelector('#stats') || tabs;
  if (anchor === tabs) tabs.before(home);
  else anchor.after(home);
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
  home.querySelector('button').onclick = () => {
    button.click();
    tabs.scrollIntoView({block: 'start'});
  };
  new MutationObserver(attach).observe(tabs, {childList: true});
})();
