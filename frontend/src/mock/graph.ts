import { Graph } from '../types';

export const mockGraph: Graph = {
  nodes: [
    {
      id: 'n1',
      label: 'What is a derivative?',
      kind: 'trunk',
      turn: {
        user: 'What is a derivative?',
        assistant:
          'A derivative measures the rate of change of a function with respect to its input. Formally, f\'(x) = lim_{h→0} (f(x+h) − f(x)) / h — the slope of the tangent line at x.',
      },
    },
    {
      id: 'n2',
      label: 'Limits',
      kind: 'prereq',
      turn: {
        user: 'I need a refresher on limits.',
        assistant:
          'A limit describes the value a function approaches as the input approaches some point. It does not require the function to be defined at that point. lim_{x→a} f(x) = L means f(x) can be made arbitrarily close to L by choosing x close enough to a.',
      },
    },
    {
      id: 'n3',
      label: 'Power rule',
      kind: 'trunk',
      turn: {
        user: 'How do I differentiate x^n?',
        assistant:
          'd/dx[x^n] = n·x^(n−1). This is the workhorse rule for polynomials — apply it term by term.',
      },
    },
    {
      id: 'n4',
      label: 'Why n·x^(n-1)?',
      kind: 'side',
      turn: {
        user: 'Why does the power rule give n·x^(n−1)?',
        assistant:
          'Expand (x+h)^n using the binomial theorem, subtract x^n, divide by h, then take h→0. All terms with h² or higher vanish, leaving n·x^(n−1).',
      },
    },
    {
      id: 'n5',
      label: 'Chain rule',
      kind: 'trunk',
      turn: {
        user: 'What is the chain rule?',
        assistant:
          'd/dx[f(g(x))] = f\'(g(x)) · g\'(x). Differentiate the outer function (leaving the inner alone), then multiply by the derivative of the inner.',
      },
    },
    {
      id: 'n6',
      label: 'Example: sin(x²)',
      kind: 'side',
      turn: {
        user: 'Can you walk me through differentiating sin(x²)?',
        assistant:
          'Outer is sin(u), inner is u = x². d/dx[sin(x²)] = cos(x²) · 2x = 2x·cos(x²).',
      },
    },
    {
      id: 'n7',
      label: 'Product rule',
      kind: 'trunk',
      turn: {
        user: 'What is the product rule?',
        assistant:
          'd/dx[f·g] = f\'·g + f·g\'. The derivative of a product is NOT the product of derivatives — both cross terms are required.',
      },
    },
    {
      id: 'n8',
      label: 'Common mistake',
      kind: 'side',
      turn: {
        user: 'Why is (fg)\' ≠ f\'·g\' a common mistake?',
        assistant:
          'It looks tempting by analogy to the sum rule, but it fails for almost every example. Try f=g=x: (x·x)\' = 2x, while x\'·x\' = 1. Always use f\'g + fg\'.',
      },
    },
    {
      id: 'n9',
      label: 'Quotient rule',
      kind: 'side',
      turn: {
        user: 'How does the quotient rule relate to the product rule?',
        assistant:
          'Write f/g = f · g^(−1) and apply product rule + chain rule. You get (f\'g − fg\') / g². So you don\'t strictly need to memorize the quotient rule.',
      },
    },
  ],
  links: [
    { source: 'n2', target: 'n1' },
    { source: 'n1', target: 'n3' },
    { source: 'n3', target: 'n4' },
    { source: 'n3', target: 'n5' },
    { source: 'n5', target: 'n6' },
    { source: 'n5', target: 'n7' },
    { source: 'n7', target: 'n8' },
    { source: 'n7', target: 'n9' },
  ],
};
