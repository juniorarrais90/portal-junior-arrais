// Página de empréstimo — versão 7
// 1) entrada suave das seções, 2) seletor de perfil,
// 3) perguntas frequentes (abre uma de cada vez), 4) balão "Como podemos ajudar?"
(() => {
  const pagina = document.querySelector('.k');
  const menosMovimento = window.matchMedia('(prefers-reduced-motion: reduce)');

  // 1. Entrada suave das seções
  if (!menosMovimento.matches && 'IntersectionObserver' in window) {
    const observador = new IntersectionObserver(itens => {
      itens.forEach(item => {
        if (item.isIntersecting) {
          item.target.classList.add('k-visivel');
          observador.unobserve(item.target);
        }
      });
    }, { threshold: 0.08 });
    document.querySelectorAll('.k-revelar').forEach(el => observador.observe(el));
    pagina.classList.add('k-animar');
    // Se a preferência mudar, todo o conteúdo continua visível.
    menosMovimento.addEventListener('change', () => {
      if (menosMovimento.matches) pagina.classList.remove('k-animar');
    });
  }

  // 2. Seletor de perfil
  const perfil = document.getElementById('k-perfil');
  const textos = {
    bolsa: ['Para quem recebe Bolsa Família', 'Confirme se há crédito disponível para o seu perfil, a natureza da operação e como as parcelas serão cobradas.'],
    inss: ['Consignado para aposentados e pensionistas', 'Consulte a disponibilidade para seu benefício e confira a margem, o custo total e as condições da proposta.'],
    clt: ['Opções para trabalhador CLT', 'Confirme as opções disponíveis para seu vínculo de trabalho e como as parcelas serão cobradas.'],
    fgts: ['Antecipação do saque-aniversário', 'Verifique as condições e entenda o impacto sobre o saldo do FGTS antes de decidir.'],
    veiculo: ['Crédito com garantia veicular', 'Consulte a avaliação, os custos e os riscos de oferecer o veículo como garantia.']
  };
  perfil.addEventListener('change', () => {
    const [titulo, descricao] = textos[perfil.value];
    document.getElementById('k-perfil-titulo').textContent = titulo;
    document.getElementById('k-perfil-descricao').textContent = descricao;
    const caixa = document.querySelector('.k-perfil-info');
    if (!menosMovimento.matches && caixa.animate) {
      caixa.animate([{ opacity: .3, transform: 'translateY(5px)' }, { opacity: 1, transform: 'none' }], { duration: 250, easing: 'ease-out' });
    }
  });

  // 3. Perguntas frequentes: abre uma, fecha as outras
  const perguntas = document.querySelectorAll('.k-faq details');
  perguntas.forEach(item => item.addEventListener('toggle', () => {
    if (item.open) perguntas.forEach(outra => { if (outra !== item) outra.open = false; });
  }));

  // 4. Balão flutuante
  const balao = document.getElementById('k-balao');
  const botaoBalao = document.getElementById('k-balao-botao');
  botaoBalao.addEventListener('click', () => {
    const aberto = balao.classList.toggle('aberto');
    botaoBalao.setAttribute('aria-expanded', aberto);
    botaoBalao.textContent = aberto ? '×' : '?';
  });
  balao.querySelectorAll('a').forEach(link => link.addEventListener('click', () => {
    balao.classList.remove('aberto');
    botaoBalao.setAttribute('aria-expanded', 'false');
    botaoBalao.textContent = '?';
  }));
})();
