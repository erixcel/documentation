#!/usr/bin/env node
/**
 * AST checks for Erixcel React. Loads TypeScript from the consumer's own
 * frontend/node_modules; no network calls and no source modifications.
 */
import { createRequire } from 'node:module';
import { resolve, join } from 'node:path';
import { readFileSync } from 'node:fs';

const [, , project, mode, ...names] = process.argv;
if (!project || !mode) {
  process.stdout.write(JSON.stringify([{ file: 'TypeScript', line: 1, rule: 'Faltan argumentos del validador AST.' }]));
  process.exit(0);
}
const require = createRequire(import.meta.url);
let ts;
try {
  ts = require(require.resolve('typescript', {
    paths: [resolve(project), join(resolve(project), 'node_modules'), process.cwd(), import.meta.dirname],
  }));
} catch (e) {
  process.stdout.write(JSON.stringify([{ file: 'TypeScript', line: 1,
    rule: 'No se encontró TypeScript para analizar el AST. Ejecuta npm install en el frontend antes de validar; el Hook no asumirá que el código cumple.' }]));
  process.exit(0);
}
const errors = [];
const isFunctionValue = value => ts.isArrowFunction(value) || ts.isFunctionExpression(value);
const lineOf = (sf, node) => sf.getLineAndCharacterOfPosition(node.getStart(sf)).line + 1;
const add = (name, sf, node, message) => errors.push({
  file: name, line: lineOf(sf, node), rule: message,
});
const hasReactHookName = name => /^use[A-Z0-9]/.test(name);
const getName = node => node?.name && ts.isIdentifier(node.name) ? node.name.text : '';

function validateFunctionsOnly(name, sf, kind) {
  let declared = [];
  for (const st of sf.statements) {
    if (ts.isImportDeclaration(st) || ts.isImportEqualsDeclaration(st)) continue;
    if (ts.isFunctionDeclaration(st)) {
      const nameOfFunction = getName(st);
      if (nameOfFunction) declared.push(nameOfFunction);
      continue;
    }
    if (ts.isVariableStatement(st)) {
      for (const d of st.declarationList.declarations) {
        if (d.initializer && isFunctionValue(d.initializer) && ts.isIdentifier(d.name)) {
          declared.push(d.name.text);
        } else {
          add(name, sf, d, 'Solo funciones a nivel superior: const/let debe inicializarse con una función flecha o expresión de función.');
        }
      }
      continue;
    }
    add(name, sf, st, 'Solo imports y funciones a nivel superior: prohibidos type, interface, class, enum, namespace, objetos, estado compartido y ejecución al importar.');
  }
  if (kind === 'hooks' && !declared.some(hasReactHookName)) {
    errors.push({ file: name, line: 1, rule: 'El archivo .hook.ts debe declarar al menos un hook useNombre; los auxiliares pueden tener otros nombres.' });
  }
  if (kind === 'services') {
    function walk(node) {
      if (ts.isJsxElement(node) || ts.isJsxSelfClosingElement(node) || ts.isJsxFragment(node)) {
        add(name, sf, node, 'Los servicios no contienen JSX; mueve el renderizado a componentes.');
        return;
      }
      if (ts.isCallExpression(node)) {
        const expr = node.expression;
        const target = ts.isIdentifier(expr) ? expr.text :
          (ts.isPropertyAccessExpression(expr) ? expr.name.text : '');
        if (hasReactHookName(target) && /^(useState|useEffect|useMemo|useCallback|useRef|useContext|useReducer|useLayoutEffect|useSyncExternalStore|use[A-Z])/.test(target)) {
          add(name, sf, node, 'Los servicios no deben invocar hooks de React (useNombre).');
        }
      }
      if (ts.isImportDeclaration(node)) {
        const source = node.moduleSpecifier.text;
        if (source === 'react-dom' || source === 'react-dom/client') {
          add(name, sf, node, 'Los servicios no deben importar ReactDOM.');
        }
      }
      ts.forEachChild(node, walk);
    }
    walk(sf);
  }
}

function validateStore(name, sf) {
  // A store may initialize singleton clients and mutable module-level state.
  // Do not apply validateFunctionsOnly to stores.
  let hasRuntimeState = false;
  const reactNamespaces = new Set(['React']);
  const reactHookAliases = new Set();
  const reactElementAliases = new Set(['createElement']);
  const reactRootAliases = new Set(['createRoot', 'hydrateRoot']);

  for (const statement of sf.statements) {
    if (ts.isVariableStatement(statement) || ts.isClassDeclaration(statement) ||
        ts.isExpressionStatement(statement)) hasRuntimeState = true;
    if (ts.isImportDeclaration(statement) && ts.isStringLiteral(statement.moduleSpecifier)) {
      const source = statement.moduleSpecifier.text;
      const clause = statement.importClause;
      if (source === 'react-dom' || source.startsWith('react-dom/')) {
        add(name, sf, statement, '[store-reactdom] Un store no importa ReactDOM ni monta componentes.');
      }
      if (source === 'react' && clause && !clause.isTypeOnly) {
        if (clause.name) reactNamespaces.add(clause.name.text);
        const bindings = clause.namedBindings;
        if (bindings && ts.isNamespaceImport(bindings)) reactNamespaces.add(bindings.name.text);
        if (bindings && ts.isNamedImports(bindings)) {
          for (const element of bindings.elements) {
            if (element.isTypeOnly) continue;
            const original = (element.propertyName ?? element.name).text;
            if (/^use[A-Z0-9]/.test(original)) reactHookAliases.add(element.name.text);
            if (original === 'createElement') reactElementAliases.add(element.name.text);
          }
        }
      }
      continue;
    }
  }

  function inspect(node) {
    if (ts.isJsxElement(node) || ts.isJsxSelfClosingElement(node) || ts.isJsxFragment(node)) {
      add(name, sf, node, '[store-jsx] Los stores no contienen JSX ni componentes React.');
      return;
    }
    if (ts.isFunctionDeclaration(node) && node.name && /^use[A-Z0-9]/.test(node.name.text)) {
      add(name, sf, node, '[store-react-hook] Define hooks useNombre en archivos .hook.ts, no en stores.');
    }
    if (ts.isCallExpression(node)) {
      const expr = node.expression;
      const direct = ts.isIdentifier(expr) ? expr.text : null;
      const property = ts.isPropertyAccessExpression(expr) ? expr : null;
      const method = property ? property.name.text : null;
      const receiver = property && ts.isIdentifier(property.expression) ? property.expression.text : null;
      const hookCall = (direct && (/^use[A-Z0-9]/.test(direct) || reactHookAliases.has(direct))) ||
        (receiver && reactNamespaces.has(receiver) && /^use[A-Z0-9]/.test(method));
      if (hookCall) add(name, sf, node, '[store-react-hook] No invoques React Hooks desde stores; usa archivos .hook.ts.');
      const renderCall = (direct && (reactElementAliases.has(direct) || reactRootAliases.has(direct))) ||
        (receiver && (reactNamespaces.has(receiver) && method === 'createElement' ||
          /^ReactDOM$/.test(receiver) && ['createRoot', 'hydrateRoot', 'render'].includes(method)));
      if (renderCall) add(name, sf, node, '[store-react-render] No crees componentes ni montes ReactDOM desde un store.');
    }
    if (ts.isVariableDeclaration(node) && ts.isIdentifier(node.name) &&
        /^use[A-Z0-9]/.test(node.name.text) && node.initializer && isFunctionValue(node.initializer)) {
      add(name, sf, node, '[store-react-hook] Los hooks React deben declararse en .hook.ts.');
    }
    ts.forEachChild(node, inspect);
  }
  inspect(sf);
  // Type-only modules are not state stores, but allow standalone store accessors
  // (e.g. a lazily cached singleton in a closure) without guessing behavior.
  const runtime = sf.statements.some(st => ts.isVariableStatement(st) ||
    ts.isFunctionDeclaration(st) || ts.isClassDeclaration(st) || ts.isExpressionStatement(st));
  if (!runtime) add(name, sf, sf, '[store-empty] No uses .store.ts solo para types/interfaces/imports; debe conservar o exponer estado/instancias.');
}

function validateStyles(name, sf) {
  function visit(node) {
    if (ts.isJsxElement(node) && node.openingElement.tagName.getText(sf).toLowerCase() === 'style') {
      add(name, sf, node, 'No uses <style>: Tailwind debe aplicarse mediante className.');
    }
    if (ts.isJsxSelfClosingElement(node) && node.tagName.getText(sf).toLowerCase() === 'style') {
      add(name, sf, node, 'No uses <style>.');
    }
    if (ts.isJsxAttribute(node) && node.name.text === 'style') {
      const expr = node.initializer && ts.isJsxExpression(node.initializer) ? node.initializer.expression : null;
      const cssVarsOnly = !!expr && ts.isObjectLiteralExpression(expr) && expr.properties.length > 0
        && expr.properties.every(prop =>
          ts.isPropertyAssignment(prop) && ts.isStringLiteral(prop.name)
          && prop.name.text.startsWith('--'));
      if (!cssVarsOnly) add(name, sf, node,
        'Evita style inline estático: utiliza className con Tailwind; solo se permiten variables CSS calculadas para utilidades Tailwind.');
    }
    if (ts.isTaggedTemplateExpression(node)) {
      const tag = node.tag.getText(sf);
      if (/^(styled(?:\.\w+)?|css)$/.test(tag)) add(name, sf, node, 'No uses CSS-in-JS; emplea utilidades Tailwind.');
    }
    ts.forEachChild(node, visit);
  }
  visit(sf);
}

for (const name of names) {
  let raw;
  try {
    raw = readFileSync(resolve(project, name), 'utf-8');
  } catch {
    continue; // Deleted file: its folder is validated by Python.
  }
  const sf = ts.createSourceFile(name, raw, ts.ScriptTarget.Latest, true,
    name.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS);
  for (const diag of sf.parseDiagnostics) {
    const at = sf.getLineAndCharacterOfPosition(diag.start ?? 0).line + 1;
    errors.push({ file: name, line: at, rule: 'No se puede analizar el TypeScript: ' + ts.flattenDiagnosticMessageText(diag.messageText, ' ') });
  }
  if (mode === 'hooks' || mode === 'services') validateFunctionsOnly(name, sf, mode);
  if (mode === 'styles') validateStyles(name, sf);
  if (mode === 'stores') validateStore(name, sf);
}
process.stdout.write(JSON.stringify(errors));
