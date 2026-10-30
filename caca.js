/* Caça ao Tesouro de Férias (31/10 a 08/11/2026).
   Cada letra e cada pista só aparecem no dia delas. A letra vem da planilha do Google,
   que também só entrega a letra do dia de hoje. */
(function () {
  var API = 'https://script.google.com/macros/s/AKfycbwxWiEy6dAJQBRXofMBediN2tup-US_Tuz1EcigZzMiKbWvhG5VZ_0p_zJxwy0MOpVv7A/exec';
  var INICIO = Date.parse('2026-10-31T00:00:00-03:00');
  var ABRE_FORMULARIO = Date.parse('2026-11-08T00:00:00-03:00');
  var FECHA_FORMULARIO = Date.parse('2026-11-09T12:00:00-03:00');
  var DIA_MS = 86400000;

  // Uma matéria por dia, na ordem das letras
  var PISTAS = [
    { url: 'bolsa-familia-novembro-2026-pagamento-comeca-dia-16.html', tema: 'o pagamento do Bolsa Família de novembro' },
    { url: 'bpc-loas-regras-2026-renda-e-revisao.html', tema: 'as regras do BPC/LOAS em 2026' },
    { url: 'prova-de-vida-do-inss-o-que-conta-sozinho-e-quando-bloqueia.html', tema: 'a prova de vida do INSS' },
    { url: 'aposentadoria-por-idade-a-idade-e-o-tempo-minimo-que-valem-hoje.html', tema: 'a aposentadoria por idade' },
    { url: 'cadunico-quando-e-obrigatorio-atualizar-o-cadastro.html', tema: 'quando atualizar o CadÚnico' },
    { url: 'aposentadoria-por-incapacidade-e-auxilio-doenca-qual-e-a-diferenca.html', tema: 'a diferença entre auxílio-doença e aposentadoria por incapacidade' },
    { url: 'bolsa-familia-regra-de-protecao-agora-e-de-18-meses.html', tema: 'a regra de proteção do Bolsa Família' },
    { url: 'acumulo-de-beneficios-o-que-da-para-receber-junto.html', tema: 'os benefícios que dá para receber juntos' },
    { url: 'tempo-de-contribuicao-por-que-conferir-o-historico-do-inss.html', tema: 'como conferir o tempo de contribuição' }
  ];

  function diaDeHoje() {
    return Math.floor((Date.now() - INICIO) / DIA_MS) + 1;
  }

  // Quadro da letra dentro da matéria: só no dia dela
  var caixa = document.getElementById('caca-tesouro');
  if (caixa) {
    var n = Number(caixa.getAttribute('data-dia'));
    if (n && diaDeHoje() === n) {
      fetch(API + '?dia=' + n)
        .then(function (r) { return r.json(); })
        .then(function (r) {
          if (!r.ok) return;
          caixa.innerHTML =
            '<div style="margin:28px 0;padding:18px 20px;border:2px dashed #2c89e7;border-radius:14px;background:#eef4fb;text-align:center">' +
            '<p style="margin:0 0 6px;font-weight:700">🔎 Caça ao Tesouro de Férias · Letra nº ' + n + ' de 9</p>' +
            '<p style="margin:0;font-size:48px;font-weight:800;color:#2c89e7;line-height:1.1">' + r.mensagem + '</p>' +
            '<p style="margin:8px 0 0;font-size:14px">Anote agora: amanhã esta letra some! ' +
            '<a href="../caca-ao-tesouro.html">Veja o regulamento e participe</a></p></div>';
        })
        .catch(function () {});
    }
  }

  // Pista de hoje na página da Caça ao Tesouro
  var pista = document.getElementById('caca-pistas');
  if (pista) {
    var hoje = diaDeHoje();
    if (hoje >= 1 && hoje <= PISTAS.length) {
      pista.innerHTML = '<p><strong>Letra nº ' + hoje + ' de 9:</strong> está escondida na matéria sobre ' +
        '<a href="noticias/' + PISTAS[hoje - 1].url + '">' + PISTAS[hoje - 1].tema + '</a>. ' +
        'Abra, procure o quadro no fim do texto e anote a letra. Amanhã tem outra!</p>';
    } else if (hoje > PISTAS.length) {
      pista.innerHTML = '<p>As 9 letras já foram reveladas. Agora é com você!</p>';
    }
  }

  // Formulário: só aparece de 08/11 até 09/11 às 12h
  var form = document.getElementById('cacada');
  if (form) {
    var agora = Date.now();
    if (agora < ABRE_FORMULARIO || agora > FECHA_FORMULARIO) {
      form.style.display = 'none';
      var aviso = document.createElement('div');
      aviso.className = 'destaque-box';
      aviso.innerHTML = agora < ABRE_FORMULARIO
        ? '<p>📅 O formulário abre aqui no dia <strong>8 de novembro</strong>, quando sai a última letra. Até lá, junte as letras!</p>'
        : '<p>As inscrições foram encerradas em 9 de novembro, às 12h. Acompanhe o resultado na live do YouTube, às 19h!</p>';
      form.parentNode.insertBefore(aviso, form);
    }
  }
})();
