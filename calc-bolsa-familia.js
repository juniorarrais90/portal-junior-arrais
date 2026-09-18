/*
 * Calculadora do Bolsa Família 2026 — módulo de cálculo
 * Júnior Arrais Advogado (OAB/MG 193.054)
 *
 * Base legal:
 *  - Lei nº 14.601/2023, art. 7º, § 1º (composição dos benefícios) e § 5º (Variável Familiar por integrante:
 *    cada pessoa recebe UM Variável Familiar, mesmo que se enquadre em mais de uma situação; por isso a página
 *    pede gestantes e nutrizes ADULTAS e manda contar a adolescente grávida/lactante só em "7 a 17 anos").
 *  - Decreto nº 12.064/2024, art. 21 (valores e ordem de cálculo; § 1º: total arredondado para o inteiro
 *    imediatamente superior; § 5º e § 6º: nutriz = família com criança que ainda não completou 7 meses,
 *    pago em 6 parcelas) e art. 33, § 3º (Regra de Proteção: 50% do valor).
 *  - Decreto nº 13.120/2026, art. 2º (novos valores) e art. 3º (efeitos financeiros a partir de outubro/2026).
 *
 * Funciona no navegador (window.CalcBolsaFamilia) e no Node (module.exports), para permitir testes.
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) { module.exports = factory(); }
  else { root.CalcBolsaFamilia = factory(); }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  var TABELAS = {
    antes: {
      id: 'antes',
      rotulo: 'Até setembro/2026',
      brc: 142,   // Benefício de Renda de Cidadania, por integrante
      piso: 600,  // Benefício Complementar: garante este valor por família
      bpi: 150,   // Benefício Primeira Infância, por criança de 0 a 7 anos incompletos
      bvf: 50,    // Benefício Variável Familiar: gestante, nutriz, 7 a 12 e 12 a 18 anos incompletos
      fonte: 'Decreto nº 12.064/2024, art. 21 (redação original)'
    },
    depois: {
      id: 'depois',
      rotulo: 'A partir de outubro/2026',
      brc: 164,
      piso: 691,
      bpi: 173,
      bvf: 58,
      fonte: 'Decreto nº 13.120/2026, art. 2º'
    }
  };

  var LIMITE_PESSOAS = 30;

  function inteiro(v) {
    var n = Number(v);
    if (!isFinite(n) || n < 0) { return 0; }
    return Math.floor(n);
  }

  function booleano(v) {
    if (typeof v === 'string') { var t = v.trim().toLowerCase(); return !(t === '' || t === '0' || t === 'false' || t === 'nao' || t === 'não'); }
    return !!v;
  }

  function normalizar(f) {
    f = f || {};
    return {
      adultos: inteiro(f.adultos),
      criancas7a17: inteiro(f.criancas7a17),
      menores7: inteiro(f.menores7),
      gestantes: inteiro(f.gestantes),
      nutrizes: inteiro(f.nutrizes),
      protecao: booleano(f.protecao)
    };
  }

  function totalPessoas(f) {
    var n = normalizar(f);
    return n.adultos + n.criancas7a17 + n.menores7;
  }

  function fracionario(v) {
    if (v === undefined || v === null || v === '') { return false; }
    var x = Number(v);
    return isFinite(x) && x !== Math.floor(x);
  }

  function validar(f) {
    var n = normalizar(f);
    var erros = [];
    var total = n.adultos + n.criancas7a17 + n.menores7;
    var bruto = f || {};
    if (['adultos', 'criancas7a17', 'menores7', 'gestantes', 'nutrizes'].some(function (k) { return fracionario(bruto[k]); })) {
      erros.push('Use números inteiros para contar as pessoas.');
    }

    if (total < 1) {
      erros.push('Informe pelo menos uma pessoa na família.');
    }
    if (total > LIMITE_PESSOAS) {
      erros.push('Confira a quantidade de pessoas: o cálculo aceita até ' + LIMITE_PESSOAS + ' integrantes.');
    }
    if (n.nutrizes > 0 && n.menores7 < 1) {
      erros.push('Para contar a nutriz, inclua o bebê entre as crianças com menos de 7 anos.');
    } else if (n.nutrizes > n.menores7) {
      erros.push('Há mais nutrizes do que bebês: cada nutriz precisa de um bebê com menos de 7 meses na família.');
    }
    if (n.gestantes + n.nutrizes > n.adultos) {
      erros.push('Gestantes e nutrizes precisam estar contadas entre os adultos. Se tiver menos de 18 anos, conte só em "7 a 17 anos".');
    }
    return { erros: erros, total: total, ok: erros.length === 0 };
  }

  function calcular(f, tabela) {
    var n = normalizar(f);
    var t = typeof tabela === 'string' ? (Object.prototype.hasOwnProperty.call(TABELAS, tabela) ? TABELAS[tabela] : null) : tabela;
    if (!t || typeof t.brc !== 'number') { throw new Error('Tabela desconhecida: ' + tabela); }

    var pessoas = n.adultos + n.criancas7a17 + n.menores7;
    // Sem integrante não há família beneficiária: nada é devido (nem Complementar, nem adicionais).
    var brc = t.brc * pessoas;
    var bco = pessoas > 0 ? Math.max(0, t.piso - brc) : 0;
    var bpi = pessoas > 0 ? t.bpi * n.menores7 : 0;
    var bvfQtd = pessoas > 0 ? n.criancas7a17 + n.gestantes + n.nutrizes : 0;
    var bvf = t.bvf * bvfQtd;
    var subtotal = brc + bco + bpi + bvf;
    // Decreto 12.064/2024, art. 21, § 1º: total arredondado ao inteiro imediatamente superior.
    // Na Regra de Proteção (art. 33, § 3º) o decreto não diz como arredondar a metade; aplica-se a mesma regra
    // (para cima). O valor processado pelo MDS pode diferir em R$ 1.
    var total = n.protecao ? Math.ceil(subtotal * 0.5) : Math.ceil(subtotal);

    return {
      tabela: t.id,
      rotulo: t.rotulo,
      fonte: t.fonte,
      piso: t.piso,
      pessoas: pessoas,
      linhas: [
        { codigo: 'brc', nome: 'Renda de Cidadania', qtd: pessoas, unitario: t.brc, valor: brc,
          detalhe: pessoas + ' pessoa' + (pessoas === 1 ? '' : 's') + ' × R$ ' + t.brc },
        { codigo: 'bco', nome: 'Complementar', qtd: bco > 0 ? 1 : 0, unitario: bco, valor: bco,
          detalhe: bco > 0 ? 'completa o piso de R$ ' + t.piso + ' por família' : 'família já passa do piso de R$ ' + t.piso },
        { codigo: 'bpi', nome: 'Primeira Infância', qtd: n.menores7, unitario: t.bpi, valor: bpi,
          detalhe: n.menores7 + ' criança' + (n.menores7 === 1 ? '' : 's') + ' com menos de 7 anos × R$ ' + t.bpi },
        { codigo: 'bvf', nome: 'Variável Familiar', qtd: bvfQtd, unitario: t.bvf, valor: bvf,
          detalhe: bvfQtd + ' pessoa' + (bvfQtd === 1 ? '' : 's') + ' (7 a 17 anos, gestantes e nutrizes) × R$ ' + t.bvf }
      ],
      subtotal: subtotal,
      protecao: n.protecao,
      total: total
    };
  }

  function comparar(f) {
    var antes = calcular(f, 'antes');
    var depois = calcular(f, 'depois');
    var diferenca = depois.total - antes.total;
    return {
      antes: antes,
      depois: depois,
      diferenca: diferenca,
      percentual: antes.total > 0 ? diferenca / antes.total : 0
    };
  }

  return {
    TABELAS: TABELAS,
    LIMITE_PESSOAS: LIMITE_PESSOAS,
    normalizar: normalizar,
    totalPessoas: totalPessoas,
    validar: validar,
    calcular: calcular,
    comparar: comparar
  };
});
