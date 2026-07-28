# Banco de imagens do Portal Júnior Arrais

Fotos para as capas das matérias. Todas em 1600x800, prontas para o gerador de capa.

**Regra de uso:** toda foto daqui exige o crédito na capa (parâmetro `--credito` do
`gerar_capa.py`) e a repetição do crédito na legenda dentro da matéria.

**Origem:** acervo Foto Agência da Agência Brasil (EBC), cuja reprodução é autorizada
mediante citação do crédito. Nunca substituir por foto de agência comercial
(Reuters, AFP, Getty, Folha), que cobra retroativamente pelo uso.

---

## Cadastro Único / CRAS

| Arquivo | O que mostra | Crédito |
|---|---|---|
| `cadunico-atendimento-social.jpg` | Plantão de atendimento da assistência social, com colete "ASSISTÊNCIA SOCIAL" visível | Foto: Tânia Rêgo/Agência Brasil |

## Bolsa Família / Caixa

| Arquivo | O que mostra | Crédito |
|---|---|---|
| `bolsa-familia-predio-caixa.jpg` | Prédio da Caixa Econômica Federal | Foto: Rafa Neddermeyer/Agência Brasil |

## BPC / LOAS

| Arquivo | O que mostra | Crédito |
|---|---|---|
| `bpc-pessoa-idosa.jpg` | Pessoa idosa trabalhando em feira (pauta de renda na terceira idade) | Foto: Marcelo Camargo/Agência Brasil |

## INSS / Previdência

| Arquivo | O que mostra | Crédito |
|---|---|---|
| `inss-previdencia-social.jpg` | Edifício sede da Previdência Social, com letreiro legível | Foto: José Cruz/Agência Brasil |

## FGTS / Trabalho

| Arquivo | O que mostra | Crédito |
|---|---|---|
| `fgts-aplicativo.jpg` | Aplicativo do FGTS na tela do celular | Foto: Joédson Alves/Agência Brasil |
| `trabalho-carteira-digital.jpg` | Carteira de Trabalho Digital no celular | Foto: Bruno Peres/Agência Brasil |

## Gás do Povo

| Arquivo | O que mostra | Crédito |
|---|---|---|
| `gas-do-povo-botijao.jpg` | Botijões de 13 kg em caminhão de distribuição | Foto: Marcello Casal Jr./Agência Brasil |

## Pé-de-Meia / Educação

| Arquivo | O que mostra | Crédito |
|---|---|---|
| `pe-de-meia-escola.jpg` | Alunos do ensino médio em sala de aula de escola pública | Foto: Rafa Neddermeyer/Agência Brasil |

## Minha Casa Minha Vida

| Arquivo | O que mostra | Crédito |
|---|---|---|
| `minha-casa-moradia-popular.jpg` | Moradora em prédio de moradia popular | Foto: Rovena Rosa/Agência Brasil |
| `minha-casa-conjunto-habitacional.jpg` | Vista aérea de conjunto do Minha Casa Minha Vida, em Fortaleza | Foto: Ricardo Stuckert/PR |

> Atenção na foto de Fortaleza: o crédito é da Presidência da República, não da Agência
> Brasil. Use preferencialmente a outra. Se usar esta, mantenha o crédito exatamente
> como está.

## Tarifa Social / Energia

| Arquivo | O que mostra | Crédito |
|---|---|---|
| `tarifa-social-interruptor.jpg` | Dedo acionando interruptor de luz | Foto: Fernando Frazão/Agência Brasil |

## Dinheiro / Orçamento familiar

| Arquivo | O que mostra | Crédito |
|---|---|---|
| `dinheiro-cedulas-reais.jpg` | Cédulas de 100 reais | Foto: Rafa Neddermeyer/Agência Brasil |

---

## Fotos descartadas na conferência

Três candidatas foram baixadas e reprovadas na conferência visual. Ficam registradas
aqui para ninguém tentar de novo:

- fila em agência da Caixa — na verdade é bilhete da Mega da Virada, remete a loteria;
- interior de agência do INSS — a imagem mostra comércio fechado, com grade e pichação;
- notas de real em foco suave — desfocada demais para servir de fundo.

**Lição:** toda foto nova entra no banco só depois de olhada. Descrição de acervo engana.

## O que ainda falta no banco

O acervo da Agência Brasil não tem foto de: cartão do Bolsa Família, fachada de CRAS,
atendimento do CadÚnico, botijão do Gás do Povo com a marca do programa, nem fachada de
agência do INSS pelo lado de fora. Quando aparecer alguma, ou quando Júnior fotografar,
é só acrescentar aqui.

## Como usar

```
python3 scripts/gerar_capa.py \
  --saida img/<slug>.png \
  --categoria "Bolsa Família" \
  --linhas "PRIMEIRA LINHA|SEGUNDA LINHA" \
  --foto-fundo img/banco/<arquivo>.jpg \
  --credito "Foto: Fulano/Agência Brasil"
```
