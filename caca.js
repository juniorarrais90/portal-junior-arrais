/* Caça ao Tesouro de Férias (31/10 a 08/11/2026).
   A letra vem da planilha do Google, que só entrega a letra de um dia a partir daquele dia. */
(function () {
  var API = 'https://script.google.com/macros/s/AKfycbwxWiEy6dAJQBRXofMBediN2tup-US_Tuz1EcigZzMiKbWvhG5VZ_0p_zJxwy0MOpVv7A/exec';
  var INICIO = Date.parse('2026-10-31T00:00:00-03:00');
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

  function dataDoDia(n) {
    var d = new Date(INICIO + (n - 1) * DIA_MS + 12 * 3600000);
    return ('0' + d.getUTCDate()).slice(-2) + '/' + ('0' + (d.getUTCMonth() + 1)).slice(-2);
  }

  // Quadro da letra dentro da matéria
  var caixa = document.getElementById('caca-tesouro');
  if (caixa) {
    var n = Number(caixa.getAttribute('data-dia'));
    if (n && diaDeHoje() >= n) {
      fetch(API + '?dia=' + n)
        .then(function (r) { return r.json(); })
        .then(function (r) {
          if (!r.ok) return;
          caixa.innerHTML =
            '<div style="margin:28px 0;padding:18px 20px;border:2px dashed #2c89e7;border-radius:14px;background:#eef4fb;text-align:center">' +
            '<p style="margin:0 0 6px;font-weight:700">🔎 Caça ao Tesouro de Férias · Letra nº ' + n + ' de 9</p>' +
            '<p style="margin:0;font-size:48px;font-weight:800;color:#2c89e7;line-height:1.1">' + r.mensagem + '</p>' +
            '<p style="margin:8px 0 0;font-size:14px">Guarde esta letra! O código só fecha com as 9. ' +
            '<a href="../caca-ao-tesouro.html">Veja o regulamento e participe</a></p></div>';
        })
        .catch(function () {});
    }
  }

  // Lista de pistas na página da Caça ao Tesouro
  var lista = document.getElementById('caca-pistas');
  if (lista) {
    var hoje = diaDeHoje();
    var html = '';
    for (var i = 0; i < PISTAS.length; i++) {
      var dia = i + 1;
      html += '<li><strong>Letra nº ' + dia + ' (' + dataDoDia(dia) + '):</strong> ' +
        (hoje >= dia
          ? 'está na matéria sobre <a href="noticias/' + PISTAS[i].url + '">' + PISTAS[i].tema + '</a>.'
          : '🔒 a pista aparece aqui no dia ' + dataDoDia(dia) + '.') +
        '</li>';
    }
    lista.innerHTML = html;
  }
})();
