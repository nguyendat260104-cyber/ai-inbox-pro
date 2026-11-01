(() => {
  const triggers = Array.from(document.querySelectorAll('[aria-controls="assistant-panel"]'));
  const dockTrigger = triggers.find((element) => element.classList.contains('orbit-button'));
  const panel = document.getElementById('assistant-panel');
  if (!dockTrigger || !panel || !triggers.length) return;

  const closeButton = panel.querySelector('.assistant-close');
  const messages = panel.querySelector('.assistant-messages');
  const promptList = panel.querySelector('.assistant-prompts');
  const composer = panel.querySelector('.assistant-composer');
  const questionInput = composer.querySelector('input');
  const activity = panel.querySelector('.assistant-activity');
  const flowSteps = Array.from(panel.querySelectorAll('.assistant-flow [data-step]'));
  const resetButton = panel.querySelector('.assistant-reset');
  const rail = document.querySelector('.orbit-stickers');
  const sampleStage = document.querySelector('.hero-stage');
  const heroCopy = document.querySelector('.hero-copy');
  const openingMessage = messages.innerHTML;
  const stepNames = ['intent', 'catalog', 'recommendation', 'handoff'];

  flowSteps.forEach((element, index) => {
    const number = document.createElement('span');
    number.className = 'assistant-step-number';
    number.setAttribute('aria-hidden', 'true');
    number.textContent = String(index + 1).padStart(2, '0');
    const label = element.textContent.trim();
    element.replaceChildren(number, document.createTextNode(label));
  });

  let returnFocusTo = dockTrigger;
  let runToken = 0;

  const setOpen = (open, source = returnFocusTo) => {
    panel.hidden = !open;
    triggers.forEach((element) => element.setAttribute('aria-expanded', String(open)));
    if (open) {
      returnFocusTo = source;
      promptList.querySelector('button')?.focus();
    } else {
      source.focus();
    }
  };

  const updateRailPosition = () => {
    if (!rail || !sampleStage) return;
    const stageBounds = sampleStage.getBoundingClientRect();
    const railBounds = rail.getBoundingClientRect();
    const copyBounds = heroCopy.getBoundingClientRect();
    const overlapsVertically = stageBounds.bottom > railBounds.top && stageBounds.top < railBounds.bottom;
    const staysOutsideProduct = stageBounds.right <= railBounds.left;
    const overlapsCopy = copyBounds.right > railBounds.left && copyBounds.left < railBounds.right && copyBounds.bottom > railBounds.top && copyBounds.top < railBounds.bottom;
    document.querySelector('.orbit-assistant').classList.toggle('channel-rail-visible', overlapsVertically && staysOutsideProduct && !overlapsCopy);
  };

  const normalize = (text) => text.toLocaleLowerCase('vi')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/đ/g, 'd')
    .trim();

  const getScenario = (rawQuestion) => {
    const text = normalize(rawQuestion);
    if (/nhan vien|tu van vien|gap nguoi|gap nhan|nguoi that|ho tro truc tiep/.test(text)) {
      return {
        kind: 'handoff',
        steps: ['intent', 'handoff'],
        answer: 'Mình đã nhận ra khách muốn gặp người thật. Trong sản phẩm hoàn chỉnh, agent sẽ chuẩn bị nội dung và chuyển cuộc hội thoại cho đúng nhân viên. Bản mẫu này không kết nối nhân sự hoặc gửi yêu cầu thật.',
        source: 'Kịch bản bàn giao · local',
        handoffTitle: 'Yêu cầu tiếp quản',
        handoffText: 'Khách muốn được nhân viên tư vấn trực tiếp.',
        handoffContext: 'Chưa gửi đi · chưa có nhân viên thật được kết nối'
      };
    }
    if (/dat (hang|chiec|ao|san pham)|muon dat|mua|chot don|len don|giu hang|lay chiec|lay ao/.test(text)) {
      return {
        kind: 'handoff',
        steps: ['intent', 'catalog', 'recommendation', 'handoff'],
        answer: 'Tín hiệu mua hàng đã được nhận diện trong tình huống mẫu. Agent không tự chốt đơn: bước đúng tiếp theo là chuẩn bị ngữ cảnh để nhân viên xác nhận sản phẩm, thông tin giao hàng và điều kiện bán.',
        source: 'Ý định mua · kịch bản local',
        handoffTitle: 'Bản nháp chuyển cho nhân viên',
        handoffText: 'Polo Classic · màu đen · size L (thông tin sản phẩm mẫu). Cần nhân viên xác nhận thông tin khách và tồn kho thực trước khi chốt.',
        handoffContext: 'Bản nháp local · không tạo đơn, không gửi tin'
      };
    }
    if (/gia|bao nhieu|khuyen mai|giam gia/.test(text)) {
      return {
        kind: 'catalog',
        steps: ['intent', 'catalog', 'recommendation'],
        answer: 'Theo catalog mẫu, Polo Classic có giá minh họa 250.000đ. Mức giá này chỉ để trình diễn cách agent tra cứu; hãy kết nối bảng giá thật trước khi dùng với khách hàng.',
        source: 'Catalog demo · AO-POLO-01 · giá minh họa'
      };
    }
    if (/size|cao|nang|ton kho|con hang|co hang|polo|mau den|san pham/.test(text)) {
      return {
        kind: 'catalog',
        steps: ['intent', 'catalog', 'recommendation'],
        answer: 'Trong catalog demo, Polo Classic màu đen size L còn 50 chiếc mẫu. Với tình huống cao 1m72, nặng 68kg, quy tắc tư vấn minh họa gợi ý size L. Đây là dữ liệu dựng sẵn, không phải tra kho trực tiếp.',
        source: 'Catalog demo · AO-POLO-01 · tồn kho mẫu: 50'
      };
    }
    return {
      kind: 'fallback',
      steps: ['intent'],
      answer: 'Đây là kịch bản local, chưa có mô hình AI để hiểu mọi câu hỏi. Bạn có thể thử một trong các nhánh: size và tồn kho, giá sản phẩm, hoặc yêu cầu nhân viên tiếp quản.',
      source: 'Giới hạn demo · không có AI backend'
    };
  };

  const setFlow = (completedSteps) => {
    let activeIndex = -1;
    if (completedSteps.length) activeIndex = Math.max(0, ...completedSteps.map((step) => stepNames.indexOf(step)));
    flowSteps.forEach((element) => {
      const stepIndex = stepNames.indexOf(element.dataset.step);
      element.classList.toggle('is-done', completedSteps.includes(element.dataset.step) && stepIndex < activeIndex);
      element.classList.toggle('is-active', completedSteps.includes(element.dataset.step) && stepIndex === activeIndex);
      if (completedSteps.includes(element.dataset.step) && stepIndex === activeIndex) {
        element.setAttribute('aria-current', 'step');
      } else {
        element.removeAttribute('aria-current');
      }
    });
  };

  const appendUserMessage = (text) => {
    const message = document.createElement('p');
    message.className = 'assistant-message user';
    message.textContent = text;
    messages.append(message);
    panel.classList.add('has-messages');
  };

  const appendAgentMessage = (scenario) => {
    const message = document.createElement('div');
    message.className = 'assistant-message';
    const meta = document.createElement('div');
    meta.className = 'assistant-response-meta';
    const avatar = document.createElement('img');
    avatar.src = '/web/assets/ai-orbit-mascot-cutout.png';
    avatar.alt = '';
    avatar.setAttribute('aria-hidden', 'true');
    const label = document.createElement('span');
    label.textContent = 'AI Sales Agent · tình huống mẫu';
    meta.append(avatar, label);

    const body = document.createElement('p');
    body.textContent = scenario.answer;
    message.append(meta, body);

    const source = document.createElement('span');
    source.className = 'assistant-response-source';
    source.textContent = scenario.source;
    messages.append(message, source);

    if (scenario.handoffTitle) {
      const handoff = document.createElement('section');
      handoff.className = 'assistant-handoff';
      handoff.setAttribute('aria-label', 'Bản xem trước ngữ cảnh bàn giao');
      const title = document.createElement('strong');
      title.textContent = scenario.handoffTitle;
      const detail = document.createElement('p');
      detail.textContent = scenario.handoffText;
      const context = document.createElement('small');
      context.textContent = scenario.handoffContext;
      handoff.append(title, detail, context);
      messages.append(handoff);
    }
    messages.scrollTop = messages.scrollHeight;
  };

  const setBusy = (busy, label = '') => {
    panel.setAttribute('aria-busy', String(busy));
    activity.hidden = !busy;
    if (label) activity.querySelector('b').textContent = label;
    promptList.querySelectorAll('button').forEach((button) => { button.disabled = busy; });
    composer.querySelector('button').disabled = busy;
  };

  const runScenario = (rawQuestion) => {
    const question = rawQuestion.trim().slice(0, 220);
    if (!question || panel.getAttribute('aria-busy') === 'true') return;

    const scenario = getScenario(question);
    const run = ++runToken;
    appendUserMessage(question);
    messages.scrollTop = messages.scrollHeight;
    questionInput.value = '';
    setBusy(true, 'Đang nhận diện nhu cầu trong kịch bản…');
    setFlow(['intent']);

    let stepPosition = 0;
    const checkpoints = scenario.steps.slice(1);
    const timer = window.setInterval(() => {
      if (run !== runToken) {
        window.clearInterval(timer);
        return;
      }
      if (stepPosition >= checkpoints.length) {
        window.clearInterval(timer);
        setBusy(false);
        setFlow(scenario.steps);
        appendAgentMessage(scenario);
        return;
      }
      const step = checkpoints[stepPosition++];
      setFlow(['intent', ...checkpoints.slice(0, stepPosition)]);
      const label = step === 'catalog' ? 'Đối chiếu catalog dựng sẵn…'
        : step === 'recommendation' ? 'Chuẩn bị đề xuất và bước tiếp theo…'
          : 'Chuẩn bị ngữ cảnh bàn giao…';
      setBusy(true, label);
      messages.scrollTop = messages.scrollHeight;
    }, 250);
  };

  const resetDemo = () => {
    runToken += 1;
    window.getSelection()?.removeAllRanges();
    messages.innerHTML = openingMessage;
    panel.classList.remove('has-messages');
    questionInput.value = '';
    setBusy(false);
    setFlow([]);
  };

  setFlow([]);
  triggers.forEach((element) => element.addEventListener('click', () => setOpen(panel.hidden, element)));
  closeButton.addEventListener('click', () => setOpen(false));
  resetButton.addEventListener('click', resetDemo);
  window.addEventListener('scroll', updateRailPosition, { passive: true });
  window.addEventListener('resize', updateRailPosition);
  updateRailPosition();
  panel.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') setOpen(false);
  });

  promptList.addEventListener('click', (event) => {
    const button = event.target.closest('button[data-question]');
    if (button) runScenario(button.dataset.question);
  });

  composer.addEventListener('submit', (event) => {
    event.preventDefault();
    runScenario(questionInput.value);
  });
})();
