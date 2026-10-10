/* Azmoon Fa: presentation only. Exam timing, submission and scoring stay upstream. */
(() => {
  'use strict';
  document.documentElement.classList.add('az-js');
  const area = document.querySelector('meta[name="azmoon-area"]')?.content || 'public';
  document.body.classList.add(`az-${area}`);
  const main = document.querySelector('#maincontent');
  const menu = document.querySelector('.scrollmenu');
  const header = document.querySelector('.header');
  if (menu && header) {
    const toggle = document.createElement('button');
    toggle.type = 'button'; toggle.className = 'az-menu-toggle'; toggle.textContent = 'فهرست';
    toggle.setAttribute('aria-controls', menu.id); toggle.setAttribute('aria-expanded', 'false');
    toggle.addEventListener('click', () => {
      const open = menu.classList.toggle('az-open'); toggle.setAttribute('aria-expanded', String(open));
    });
    header.append(toggle);
    menu.querySelectorAll('li').forEach((li, index) => {
      const sub = li.querySelector(':scope > ul');
      if (!sub) return;
      sub.id ||= `az-submenu-${index}`;
      const button = document.createElement('button');
      button.type = 'button'; button.className = 'az-submenu-toggle'; button.textContent = '⌄';
      button.setAttribute('aria-label', `زیرمنوی ${li.firstElementChild?.textContent || ''}`);
      button.setAttribute('aria-expanded', 'false'); button.setAttribute('aria-controls', sub.id);
      button.addEventListener('click', () => {
        const open = li.classList.toggle('az-open'); button.setAttribute('aria-expanded', String(open));
      });
      li.insertBefore(button, sub);
    });
    menu.addEventListener('keydown', event => {
      if (event.key !== 'Escape') return;
      menu.querySelectorAll('.az-open').forEach(li => {
        li.classList.remove('az-open'); li.querySelector(':scope > button')?.setAttribute('aria-expanded', 'false');
      });
      menu.classList.remove('az-open'); toggle.setAttribute('aria-expanded', 'false'); toggle.focus();
    });
  }
  main?.querySelectorAll('table').forEach(table => {
    if (table.parentElement.closest('table') || table.parentElement.classList.contains('az-table-wrap')) return;
    const wrap = document.createElement('div'); wrap.className = 'az-table-wrap';
    wrap.tabIndex = 0; wrap.setAttribute('role', 'region');
    wrap.setAttribute('aria-label', table.querySelector('caption')?.textContent || 'جدول اطلاعات؛ برای مشاهده ستون‌ها پیمایش کنید');
    table.before(wrap); wrap.append(table);
  });
  if (main && /(?:^|\/)index\.php$|\/$/.test(location.pathname) && !document.querySelector('#form_login')) {
    const hero = document.createElement('section'); hero.className = 'az-hero';
    const content = document.createElement('div');
    const eyebrow = document.createElement('small'); eyebrow.textContent = area === 'admin' ? 'مدیریت آموزش و سنجش' : 'مسیر یادگیری شما';
    const title = document.createElement('h2'); title.textContent = area === 'admin' ? 'یک نگاه، همه آزمون‌ها' : 'آماده یک قدم تازه؟';
    const description = document.createElement('p'); description.textContent = area === 'admin' ? 'درس‌ها، سؤال‌ها، شرکت‌کنندگان و نتایج را از فهرست مدیریت کنید.' : 'آزمون‌های در دسترس را ببینید و کارنامه تلاش‌های قبلی را مرور کنید.';
    content.append(eyebrow, title, description);
    const mark = document.createElement('span'); mark.className = 'az-hero-mark'; mark.textContent = '✓'; mark.setAttribute('aria-hidden', 'true');
    hero.append(content, mark); main.querySelector('h1')?.after(hero);
  }
  const testform = document.querySelector('#testform');
  if (testform) {
    document.body.classList.add('az-exam');
    const hint = document.createElement('p'); hint.className = 'az-exam-hint';
    hint.textContent = 'پاسخ‌ها با ثبت پاسخ یا رفتن به سؤال دیگر ارسال می‌شوند. برای خروج، ابتدا آزمون را پایان دهید.';
    testform.before(hint);
    const status = document.createElement('p'); status.className = 'az-online-status'; status.setAttribute('role', 'status');
    const updateNetwork = () => {
      status.textContent = navigator.onLine ? 'اتصال دستگاه برقرار است؛ ثبت پاسخ نیاز به ارتباط با سرور دارد.' : 'اتصال دستگاه قطع است. پاسخ را حفظ کنید و پس از اتصال دوباره ثبت کنید.';
      status.classList.toggle('az-offline', !navigator.onLine);
    };
    updateNetwork(); window.addEventListener('online', updateNetwork); window.addEventListener('offline', updateNetwork);
    testform.before(status);
    let dirty = false; let submitting = false;
    testform.addEventListener('change', event => { if (event.target.matches('[name^=answpos],#answertext,#testcomment')) dirty = true; });
    testform.addEventListener('submit', () => { submitting = true; });
    window.addEventListener('beforeunload', event => { if (dirty && !submitting) { event.preventDefault(); event.returnValue = ''; } });
    const list = testform.querySelector('.qlist');
    if (list) {
      const all = [...list.children];
      all.forEach((li, index) => { const input = li.querySelector('input'); if (input) { input.value = (index + 1).toLocaleString('fa-IR'); input.setAttribute('aria-label', `سؤال ${(index + 1).toLocaleString('fa-IR')}`); } });
      const current = Math.max(1, all.findIndex(li => li.classList.contains('selected')) + 1);
      const progress = document.createElement('div'); progress.className = 'az-progress';
      const label = document.createElement('span'); label.textContent = `سؤال ${current.toLocaleString('fa-IR')} از ${all.length.toLocaleString('fa-IR')}`;
      const bar = document.createElement('progress'); bar.max = all.length; bar.value = current; bar.setAttribute('aria-label', 'جایگاه سؤال فعلی');
      progress.append(label, bar); testform.prepend(progress);
    }
  }
  const login = document.querySelector('#form_login');
  if (login) {
    login.querySelector('input[type=password]')?.setAttribute('autocomplete','current-password');
    login.querySelector('input[name=xuser_name],input[name=user_name]')?.setAttribute('autocomplete','username');
  }
})();
