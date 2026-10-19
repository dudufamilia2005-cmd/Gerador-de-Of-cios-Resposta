// Tela do gerador de ofícios. Conversa com o servidor local em oficios/servidor.py.
'use strict';

let CAT = null;                       // catálogo vindo do servidor
let modeloAtual = null;               // modelo escolhido na lista
let setorFiltro = '';                 // aba de setor ('' = todos)
const valores = new Map();            // "campo" -> texto digitado (compartilhado entre modelos)

const $ = (id) => document.getElementById(id);

function escaparHtml(valor) {
  const e = document.createElement('span');
  e.textContent = String(valor ?? '');
  return e.innerHTML;
}

// Preferência só desta máquina: quem assina costuma ser sempre a mesma pessoa.
const lembra = {
  le(chave) { try { return localStorage.getItem('oficios.' + chave) || ''; } catch { return ''; } },
  grava(chave, v) { try { localStorage.setItem('oficios.' + chave, v); } catch { /* sem armazenamento */ } },
};

async function requisicao(caminho, opcoes = {}) {
  const headers = new Headers(opcoes.headers || {});
  if (opcoes.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
  const resposta = await fetch(caminho, {...opcoes, headers});
  const texto = await resposta.text();
  let dados = {};
  try {
    dados = texto ? JSON.parse(texto) : {};
  } catch {
    throw new Error('O servidor respondeu em um formato inesperado. Atualize a página e tente novamente.');
  }
  if (!resposta.ok) throw new Error(dados.erro || `Não foi possível concluir a operação (${resposta.status}).`);
  return dados;
}

// ------------------------------------------------------------------- início

async function iniciar() {
  CAT = await requisicao('api/catalogo');

  desenhaAbas();
  desenhaLista();

  for (const [sigla, nome] of Object.entries(CAT.setores)) {
    const o = document.createElement('option');
    o.value = sigla; o.textContent = `${sigla} — ${nome}`;
    $('setor').append(o);
  }
  $('ano').value = CAT.ano;
  $('data').value = CAT.hoje;

  preencheCadastro();
  preencheTratamentos();
  preencheAssinantes();

  $('filtro').addEventListener('input', desenhaLista);
  $('setor').addEventListener('change', () => { sugereNumero(); pedePrevia(); });
  $('ano').addEventListener('change', () => { sugereNumero(); pedePrevia(); });
  for (const id of ['numero', 'data', 'dest-nome', 'dest-linhas', 'dest-cidade', 'vocativo',
                    'oficio-recebido', 'processo', 'assina-nome', 'assina-cargo'])
    $(id).addEventListener('input', pedePrevia);
  $('tratamento').addEventListener('change', () => {
    const t = CAT.tratamentos[$('tratamento').value];
    if (t && t.vocativo && !$('vocativo').dataset.editado) $('vocativo').value = t.vocativo;
    pedePrevia();
  });
  $('vocativo').addEventListener('input', () => { $('vocativo').dataset.editado = '1'; });
  // número digitado à mão não é atropelado pela sugestão
  $('numero').addEventListener('input', () => { $('numero').dataset.editado = '1'; });
  $('cadastro').addEventListener('change', aplicaCadastro);
  $('assinante').addEventListener('change', aplicaAssinante);
  $('gerar').addEventListener('click', () => gerar(false));
  $('limpar').addEventListener('click', novoOficio);
  $('modal-fechar').addEventListener('click', () => $('modal').hidden = true);

  aplicaAssinante();
  desenhaCampos();
  atualizaPrevia();
}

// ------------------------------------------------------------ lista de modelos

function desenhaAbas() {
  const abas = $('setores');
  const contagem = {};
  const gerais = CAT.modelos.filter(m => m.setor === '*').length;   // aparecem em todas as abas
  for (const m of CAT.modelos) if (m.setor !== '*') contagem[m.setor] = (contagem[m.setor] || 0) + 1;
  for (const s of Object.keys(contagem)) contagem[s] += gerais;
  const opcoes = [['', `Todos (${CAT.modelos.length})`],
                  ...Object.keys(CAT.setores).filter(s => contagem[s])
                                             .map(s => [s, `${s} (${contagem[s]})`])];
  for (const [sigla, rotulo] of opcoes) {
    const b = document.createElement('button');
    b.type = 'button'; b.className = 'aba'; b.textContent = rotulo;
    b.setAttribute('role', 'tab');
    b.setAttribute('aria-selected', String(sigla === setorFiltro));
    b.title = sigla ? CAT.setores[sigla] : 'Todos os setores';
    b.addEventListener('click', () => {
      setorFiltro = sigla;
      for (const x of abas.children) x.setAttribute('aria-selected', String(x === b));
      desenhaLista();
    });
    abas.append(b);
  }
}

function semAcento(t) {
  return t.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
}

function desenhaLista() {
  const termo = semAcento($('filtro').value.trim());
  const lista = $('lista');
  lista.textContent = '';
  const visiveis = CAT.modelos.filter(m =>
    (!setorFiltro || m.setor === setorFiltro || m.setor === '*') &&
    (!termo || semAcento(`${m.rotulo} ${m.grupo} ${m.descricao} ${m.setor}`).includes(termo)));

  if (!visiveis.length) {
    lista.innerHTML = '<div class="vazio">Nenhum modelo com esse termo.</div>';
    return;
  }
  let grupo = null;
  for (const m of visiveis) {
    const g = m.setor === '*' ? (m.grupo || 'Geral') : `${m.setor} · ${m.grupo || 'Outros'}`;
    if (g !== grupo) {
      grupo = g;
      const h = document.createElement('div');
      h.className = 'grupo-lista';
      h.textContent = g;
      lista.append(h);
    }
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'item' + (modeloAtual && modeloAtual.id === m.id ? ' marcado' : '');
    const texto = document.createElement('div');
    const nome = document.createElement('div');
    nome.className = 'nome'; nome.textContent = m.rotulo;
    texto.append(nome);
    if (m.descricao) {
      const meta = document.createElement('div');
      meta.className = 'meta'; meta.textContent = m.descricao;
      texto.append(meta);
    }
    b.append(texto);
    b.addEventListener('click', () => escolheModelo(m));
    lista.append(b);
  }
}

function escolheModelo(m) {
  const trocouSetor = m.setor !== '*' && (!modeloAtual || modeloAtual.setor !== m.setor
                                          || $('setor').value !== m.setor);
  modeloAtual = m;
  $('escolhido').textContent = m.setor === '*' ? m.rotulo : `${m.setor} · ${m.rotulo}`;
  if (trocouSetor) {
    $('setor').value = m.setor;
    sugereNumero();
  }
  // destinatário típico do modelo (ex.: INCRA), só se ainda não há um escolhido
  if (m.destinatario && !$('dest-nome').value.trim()) {
    $('cadastro').value = m.destinatario;
    aplicaCadastro();
  }
  $('grupo-referencia').hidden = m.referencia === false;
  desenhaLista();
  desenhaCampos();
  pedePrevia();
}

// ------------------------------------------------------------------ numeração

async function sugereNumero() {
  const alvo = $('sugestao');
  alvo.textContent = '';
  if (CAT.somente_leitura) return;
  try {
    const r = await requisicao(`api/proximo?setor=${encodeURIComponent($('setor').value)}`
                               + `&ano=${encodeURIComponent($('ano').value)}`);
    if (r.numero) {
      alvo.textContent = r.ultimo ? `último: ${r.ultimo.slice(0, 48)}${r.ultimo.length > 48 ? '…' : ''}` : r.motivo || '';
      if (!$('numero').dataset.editado || !$('numero').value.trim()) {
        $('numero').value = r.numero;
        pedePrevia();
      } else {
        const usa = document.createElement('button');
        usa.type = 'button'; usa.textContent = `usar ${r.numero}`;
        usa.addEventListener('click', () => {
          $('numero').value = r.numero; delete $('numero').dataset.editado; pedePrevia();
        });
        alvo.append(' ', usa);
      }
    } else {
      alvo.textContent = r.motivo || '';
    }
  } catch (erro) {
    alvo.textContent = erro.message;
  }
}

// --------------------------------------------------------------- destinatário

function preencheCadastro() {
  const sel = $('cadastro');
  sel.append(new Option('— digitar —', ''));
  const grupos = {};
  for (const d of CAT.destinatarios) (grupos[d.grupo || 'Outros'] ||= []).push(d);
  for (const [nome, itens] of Object.entries(grupos)) {
    const og = document.createElement('optgroup');
    og.label = nome;
    for (const d of itens) og.append(new Option(d.rotulo, d.id));
    sel.append(og);
  }
}

function preencheTratamentos() {
  const sel = $('tratamento');
  sel.append(new Option('— escolha —', ''));
  for (const [id, t] of Object.entries(CAT.tratamentos))
    sel.append(new Option(t.texto || t.rotulo, id));
}

function aplicaCadastro() {
  const d = CAT.destinatarios.find(x => x.id === $('cadastro').value);
  if (!d) return pedePrevia();
  $('tratamento').value = d.tratamento || '';
  $('dest-nome').value = d.nome || '';
  $('dest-linhas').value = (d.linhas || []).join('\n');
  $('dest-cidade').value = d.cidade || '';
  const t = CAT.tratamentos[d.tratamento] || {};
  $('vocativo').value = d.vocativo || t.vocativo || '';
  delete $('vocativo').dataset.editado;
  pedePrevia();
}

function destinatario() {
  const d = CAT.destinatarios.find(x => x.id === $('cadastro').value) || {};
  return {
    tratamento: $('tratamento').value,
    nome: $('dest-nome').value.trim(),
    linhas: $('dest-linhas').value.split('\n').map(x => x.trim()).filter(Boolean),
    cidade: $('dest-cidade').value.trim(),
    vocativo: $('vocativo').value.trim(),
    // gênero e pronome vêm do cadastro quando o tratamento não decide sozinho
    genero: d.genero || '',
    pronome: d.pronome || '',
  };
}

// ----------------------------------------------------------------- assinatura

function preencheAssinantes() {
  // Começa em branco: assinatura errada num ofício é pior que campo vazio. Na
  // segunda vez a máquina já lembra quem costuma assinar.
  const sel = $('assinante');
  sel.append(new Option('— escolha —', ''));
  for (const a of CAT.assinantes) sel.append(new Option(`${a.nome} — ${a.cargo}`, a.id));
  sel.append(new Option('— outra pessoa —', 'outra'));
  const ultimo = lembra.le('assinante');
  if (ultimo && CAT.assinantes.some(a => a.id === ultimo)) sel.value = ultimo;
}

function aplicaAssinante() {
  const id = $('assinante').value;
  $('linha-assina-nome').hidden = id !== 'outra';
  $('linha-assina-cargo').hidden = id !== 'outra';
  if (id && id !== 'outra') lembra.grava('assinante', id);
  pedePrevia();
}

function assinante() {
  const id = $('assinante').value;
  const a = CAT.assinantes.find(x => x.id === id);
  if (a) return {nome: a.nome, cargo: a.cargo};
  if (id === 'outra') return {nome: $('assina-nome').value.trim(), cargo: $('assina-cargo').value.trim()};
  return {nome: '', cargo: ''};
}

// ------------------------------------------------------------ campos do modelo

function desenhaCampos() {
  const alvo = $('campos');
  alvo.textContent = '';
  if (!modeloAtual) {
    $('titulo-campos').textContent = 'Dados do modelo';
    alvo.innerHTML = '<div class="nada">Escolha um modelo na lista ao lado.</div>';
    return;
  }
  $('titulo-campos').textContent = modeloAtual.rotulo;
  if (modeloAtual.descricao) {
    const p = document.createElement('p');
    p.className = 'descricao'; p.textContent = modeloAtual.descricao;
    alvo.append(p);
  }
  if (!modeloAtual.campos.length) {
    alvo.insertAdjacentHTML('beforeend', '<div class="nada">Este modelo não pede nenhum dado.</div>');
    return;
  }
  for (const c of modeloAtual.campos) {
    const info = CAT.campos[c] || {};
    const linha = document.createElement('div');
    linha.className = 'linha' + (info.tipo === 'longo' ? ' topo-label' : '');
    const lab = document.createElement('label');
    lab.textContent = info.rotulo || c;
    lab.htmlFor = 'campo-' + c;
    const opcional = info.padrao || !modeloAtual.obrigatorios.includes(c);
    if (opcional) {
      const op = document.createElement('span');
      op.className = 'opcional'; op.textContent = ' (opcional)';
      lab.append(op);
    }

    let inp;
    if (info.opcoes) {
      inp = document.createElement('select');
      inp.append(new Option(opcional ? '— não informar —' : '— escolha —', ''));
      const nomes = Array.isArray(info.opcoes) ? info.opcoes : Object.keys(info.opcoes);
      for (const o of nomes) inp.append(new Option(o, o));
    } else if (info.tipo === 'longo') {
      inp = document.createElement('textarea');
      inp.rows = c === 'texto_livre' ? 10 : 4;
      inp.placeholder = info.exemplo || '';
    } else if (info.tipo === 'data') {
      inp = document.createElement('input');
      inp.type = 'date';
    } else {
      inp = document.createElement('input');
      inp.autocomplete = 'off';
      inp.placeholder = info.exemplo || '';
    }
    inp.id = 'campo-' + c;
    if (!valores.get(c) && info.auto === 'mes_anterior') valores.set(c, mesAnterior());
    inp.value = valores.get(c) || '';
    if (info.ajuda) inp.title = info.ajuda;
    else if (info.padrao) inp.title = `Em branco, o ofício diz: "${info.padrao}"`;
    else if (opcional) inp.title = 'Em branco, o trecho não entra no ofício.';
    inp.addEventListener(info.opcoes ? 'change' : 'input', () => {
      valores.set(c, inp.value);
      pedePrevia();
    });
    linha.append(lab, inp);
    alvo.append(linha);
  }
}

// Comunicação mensal (INCRA): o mês de referência é o anterior à data do ofício.
const MESES = ['JANEIRO', 'FEVEREIRO', 'MARÇO', 'ABRIL', 'MAIO', 'JUNHO', 'JULHO',
               'AGOSTO', 'SETEMBRO', 'OUTUBRO', 'NOVEMBRO', 'DEZEMBRO'];
function mesAnterior() {
  const [a, m] = ($('data').value || CAT.hoje).split('-').map(Number);
  const mes = m === 1 ? 12 : m - 1;
  return `${MESES[mes - 1]} - ${m === 1 ? a - 1 : a}`;
}

// --------------------------------------------------------------------- prévia

function montaPedido() {
  const v = {};
  if (modeloAtual) for (const c of modeloAtual.campos) v[c] = (valores.get(c) || '').trim();
  return {
    modelo: modeloAtual ? modeloAtual.id : '',
    setor: $('setor').value,
    ano: $('ano').value.trim(),
    numero: $('numero').value.trim(),
    data: $('data').value,
    destinatario: destinatario(),
    oficio_recebido: modeloAtual && modeloAtual.referencia === false ? '' : $('oficio-recebido').value.trim(),
    processo: modeloAtual && modeloAtual.referencia === false ? '' : $('processo').value.trim(),
    valores: v,
    assinante: assinante(),
  };
}

let relogioPrevia;
function pedePrevia() {
  clearTimeout(relogioPrevia);
  relogioPrevia = setTimeout(atualizaPrevia, 300);
}

async function atualizaPrevia() {
  const alvo = $('previa');
  if (!modeloAtual) {
    alvo.innerHTML = '<div class="vazio">O ofício aparece aqui assim que você escolhe um modelo.</div>';
    $('previa-aviso').textContent = '';
    $('aviso').textContent = '';
    return;
  }
  try {
    const res = await requisicao('api/previa', {method: 'POST', body: JSON.stringify(montaPedido())});
    // O servidor devolve 200 com {html:"", erro:"..."} quando a montagem falha.
    alvo.innerHTML = res.html || `<div class="vazio">${escaparHtml(res.erro || 'Sem conteúdo.')}</div>`;
    const falta = res.faltando || [];
    $('previa-aviso').textContent = falta.length ? `falta: ${falta.join(', ')}` : '';
    $('aviso').textContent = falta.length ? `${falta.length} item(ns) por preencher` : '';
  } catch (erro) {
    alvo.innerHTML = `<div class="vazio">${escaparHtml(erro.message)}</div>`;
  }
}

// ---------------------------------------------------------------------- gerar

function baixa(base64, nome) {
  const bytes = Uint8Array.from(atob(base64), c => c.charCodeAt(0));
  const url = URL.createObjectURL(new Blob([bytes],
    {type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'}));
  const a = document.createElement('a');
  a.href = url; a.download = nome;
  document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 5000);
}

function avisa(titulo, html, {caminho = null, extra = null} = {}) {
  $('modal-titulo').textContent = titulo;
  $('modal-corpo').innerHTML = html;
  const pasta = $('modal-pasta');
  pasta.hidden = !caminho;
  pasta.onclick = caminho ? () => requisicao('api/abrir-pasta', {
    method: 'POST', body: JSON.stringify({caminho}),
  }).catch(() => {}) : null;
  const b = $('modal-extra');
  b.hidden = !extra;
  if (extra) { b.textContent = extra.rotulo; b.onclick = extra.acao; }
  $('modal').hidden = false;
}

async function gerar(sobrescrever) {
  if (!modeloAtual) return avisa('Escolha um modelo', '<p>Selecione na lista o tipo de ofício.</p>');
  $('gerar').disabled = true;
  try {
    const res = await requisicao('api/gerar', {
      method: 'POST', body: JSON.stringify({...montaPedido(), sobrescrever}),
    });
    if (!res.ok) {
      if (res.existe) {
        return avisa('Já existe', `<p>Já há um ofício com este nome em <em>saida</em>:</p>
          <div class="caminho">${escaparHtml(res.arquivo)}</div>
          <p>Confira o número. Se for mesmo para substituir, use o botão abaixo.</p>`,
          {extra: {rotulo: 'Substituir', acao: () => { $('modal').hidden = true; gerar(true); }}});
      }
      return avisa('Falta preencher', `<p>${escaparHtml(res.erro)}</p>`);
    }
    if (res.conteudo) {
      baixa(res.conteudo, res.arquivo);
      avisa('Ofício gerado', `<p>Ofício gerado e baixado:</p><div class="caminho">${escaparHtml(res.arquivo)}</div>`);
    } else {
      avisa('Ofício gerado', `<p>Ofício gravado em:</p><div class="caminho">${escaparHtml(res.caminho)}</div>
        <p>Confira no Word antes de assinar e arquivar na pasta do setor.</p>`, {caminho: res.caminho});
      sugereNumero();
    }
  } catch (erro) {
    avisa('Não foi possível gerar', `<p>${escaparHtml(erro.message)}</p>`);
  } finally {
    $('gerar').disabled = false;
  }
}

function novoOficio() {
  valores.clear();
  for (const id of ['dest-nome', 'dest-linhas', 'dest-cidade', 'vocativo', 'oficio-recebido', 'processo'])
    $(id).value = '';
  $('cadastro').value = '';
  $('tratamento').value = '';
  delete $('vocativo').dataset.editado;
  delete $('numero').dataset.editado;
  $('data').value = CAT.hoje;
  desenhaCampos();
  sugereNumero();
  pedePrevia();
}

iniciar().catch(erro => {
  $('lista').innerHTML = `<div class="vazio">${escaparHtml(erro.message)}</div>`;
  $('gerar').disabled = true;
});
