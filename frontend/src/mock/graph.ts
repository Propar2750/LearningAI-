import type { Graph } from '../types';

// Trunk of 4 + two side branches + one prerequisite cross-link.
// Enough to exercise trunk pinning, ancestor highlighting, and edge styling.
export const mockGraph: Graph = {
  goal: { text: 'Understand backpropagation in neural networks' },
  nodes: [
    {
      id: 'n1',
      prompt: 'What is a neural network?',
      reply: `A neural network is a parameterized function that maps inputs to outputs by stacking simple building blocks — called layers — on top of each other. Each layer takes the vector produced by the previous layer, multiplies it by a matrix of learned weights, adds a bias vector, and then passes the result through a nonlinear "activation" function. That nonlinearity is what makes the whole stack more expressive than a single matrix multiplication; without it, no matter how many layers you stack, the network would collapse into a plain linear map.

The "learning" part comes from the weights and biases. They start as small random numbers and are updated based on how wrong the network's predictions are on training data. Over many updates, the network gradually shapes itself into a function that fits the patterns in the data — recognizing digits in images, predicting the next token in text, scoring chess positions, and so on.

A few mental models that often help:
  • Think of each layer as extracting features from the layer below. Early layers might detect edges in an image; later layers combine those into shapes, then objects.
  • Think of the whole network as a giant differentiable function. "Differentiable" is the key word — it's what lets us use calculus (specifically the chain rule, via backpropagation) to figure out how to adjust every weight to reduce the error.
  • Think of training as search. You're searching a very high-dimensional space of weight configurations for one that explains the data well.

This is the foundation everything else builds on: forward pass (compute outputs), loss (measure how wrong), backward pass (compute gradients), and weight update (take a small step in a better direction).`,
      summary: 'Definition of neural network.',
      parentIds: [],
      createdAt: 1,
      isTrunk: true,
    },
    {
      id: 'n2',
      prompt: 'How does a single neuron compute its output?',
      reply: `A single neuron is the smallest unit of computation in a neural network, and despite the biological-sounding name, what it actually does is very simple arithmetic. Given an input vector x = [x₁, x₂, …, xₙ], the neuron has a matching weight vector w = [w₁, w₂, …, wₙ] and a single bias scalar b. It computes:

    z = w₁·x₁ + w₂·x₂ + … + wₙ·xₙ + b
      = w · x + b           (dot product plus bias)

That value z is called the pre-activation. By itself it's still just a linear function of the inputs, which means a whole network of these would be no more expressive than one big linear map. To fix that, we pass z through a nonlinear activation function — most commonly ReLU, but also sigmoid, tanh, GELU, etc.:

    a = activation(z)

The output a is what the neuron passes on to the next layer. In modern implementations you never actually loop over individual neurons; an entire layer of them is computed in one matrix multiply: A = activation(X · W + b), where X is a batch of inputs and W stacks all the per-neuron weight vectors as columns. That vectorization is what makes GPUs so effective for neural nets — the same tiny operation happens millions of times in parallel.

Two things to keep in mind:
  • The weights and bias are what get learned during training; the activation function is fixed up front.
  • The choice of activation has real consequences for gradient flow during backpropagation — saturating activations like sigmoid can cause gradients to vanish in deep networks, which is a big part of why ReLU became the default.`,
      summary: 'Single-neuron forward pass.',
      parentIds: ['n1'],
      createdAt: 2,
      isTrunk: true,
    },
    {
      id: 'n3',
      prompt: 'What is a loss function?',
      reply: `A loss function is a scalar-valued function that measures how wrong the model's predictions are compared to the true targets. It's the signal that drives all of learning: training is, mechanically, the process of nudging weights in whatever direction makes this number smaller, averaged over the training data.

A few common choices and when they're used:
  • Mean Squared Error (MSE):  L = (1/n) Σ (ŷᵢ − yᵢ)²
    Used for regression, where the target is a real number. Penalizes large errors quadratically, so outliers dominate.
  • Mean Absolute Error (MAE): L = (1/n) Σ |ŷᵢ − yᵢ|
    Also regression, but more robust to outliers because the penalty grows linearly.
  • Binary Cross-Entropy:  L = −[y log(ŷ) + (1−y) log(1−ŷ)]
    Used for binary classification with a sigmoid output. Treats the output as a probability.
  • Categorical Cross-Entropy:  L = −Σ yᵢ log(ŷᵢ)
    Used for multi-class classification with a softmax output. Strongly penalizes confident wrong predictions.

Two properties matter for a loss to be usable in deep learning:
  1. Differentiable (almost everywhere) with respect to the model's outputs — otherwise we couldn't backpropagate gradients through it.
  2. Aligned with the actual goal — minimizing the loss should correspond to the behavior you actually want. A model can achieve low loss while still being wrong in ways the loss doesn't capture, which is why metric choice is its own art.

You'll also frequently see a regularization term added: L_total = L_data + λ · R(w), where R(w) penalizes large weights (L2) or encourages sparsity (L1). This biases the optimizer toward simpler solutions and helps with generalization.`,
      summary: 'Loss function basics.',
      parentIds: ['n2'],
      createdAt: 3,
      isTrunk: true,
    },
    {
      id: 'n4',
      prompt: 'How does backpropagation update weights?',
      reply: `Backpropagation is the algorithm that figures out, for every single weight in the network, how much that weight contributed to the final loss — and therefore in which direction it should be nudged to reduce that loss. It is mechanically just the chain rule from calculus, applied carefully across the network's computation graph.

The full training step has two phases:

1. Forward pass. You feed an input through the network, computing each layer's activations in order. Along the way, you cache the intermediate values (pre-activations, activations, inputs to each layer) because the backward pass will need them.

2. Backward pass. Starting from the loss at the output, you walk backward through the layers, computing the gradient of the loss with respect to each layer's outputs, then propagating that gradient through the layer's local operations to get gradients with respect to the layer's inputs and its weights. Concretely, for a layer doing z = W·x + b followed by a = σ(z):
       ∂L/∂z = ∂L/∂a · σ'(z)
       ∂L/∂W = ∂L/∂z · xᵀ
       ∂L/∂b = ∂L/∂z
       ∂L/∂x = Wᵀ · ∂L/∂z      ← passed to the previous layer

That last quantity — the gradient with respect to the input — is exactly what the previous layer needs to start its own backward step. So the gradient flows backward through the network the same way the activations flowed forward.

Once every weight has a gradient, the optimizer takes a step:
       W ← W − η · ∂L/∂W
where η is the learning rate. Variants like SGD with momentum, Adam, and AdamW change how that step is computed (using running averages, per-parameter learning rates, decoupled weight decay), but they all rely on the gradients produced by backprop.

The reason this is efficient is that backprop reuses partial gradients across the graph — every shared subexpression is computed once and reused, giving the whole pass the same asymptotic cost as the forward pass. Without that trick, training large networks would be computationally hopeless.`,
      summary: 'Backprop weight update.',
      parentIds: ['n3'],
      createdAt: 4,
      isTrunk: true,
    },
    {
      id: 's1',
      prompt: 'Wait, what is ReLU exactly?',
      reply: `ReLU stands for "Rectified Linear Unit," and despite the intimidating name it's the simplest activation function in wide use:

       ReLU(x) = max(0, x)

If the input is positive, it passes through unchanged. If it's negative, it's clamped to zero. That's it. The derivative is equally simple: 1 for positive inputs, 0 for negative inputs (and technically undefined at exactly 0, but in practice it's treated as 0).

Why this tiny function became the default activation in deep learning:
  • Cheap to compute — just a comparison and a select, no exp or division.
  • Non-saturating on the positive side, so gradients don't shrink as activations grow. This was the main fix for the "vanishing gradient" problem that made deep sigmoid/tanh networks nearly untrainable.
  • Naturally sparse — about half the neurons output zero on any given input, which acts as a mild form of regularization and can make downstream computations more efficient.

The main downside is the "dying ReLU" problem: if a neuron's weights get pushed into a regime where it always outputs zero, its gradient is also always zero, so it can never recover. Variants exist to address this:
  • Leaky ReLU:     f(x) = x if x > 0 else 0.01·x
  • Parametric ReLU: same form, but the negative slope is learned.
  • GELU and SiLU:  smooth approximations that are now standard in transformers.

For most everyday work, plain ReLU in hidden layers is still a reasonable default; modern language models tend to prefer GELU/SiLU because the smoothness plays better with very deep architectures.`,
      summary: 'ReLU definition.',
      parentIds: ['n2'],
      createdAt: 5,
      isTrunk: false,
    },
    {
      id: 's2',
      prompt: 'Why cross-entropy and not MSE for classification?',
      reply: `It comes down to how the loss interacts with the model's output layer and how informative the resulting gradients are.

For classification, the network's final layer is usually a softmax that turns raw scores (logits) into a probability distribution over classes. Cross-entropy is the natural loss in that setting because it has a clean information-theoretic interpretation: it measures the number of extra bits you'd need to encode the true labels using the model's predicted distribution. Minimizing it is equivalent to maximum-likelihood estimation under a categorical model.

Mechanically, the magic happens when you compose softmax with cross-entropy. The gradient of the combined operation with respect to the logits simplifies beautifully to:

       ∂L/∂zᵢ = ŷᵢ − yᵢ

That is, "predicted probability minus true label." This gradient is:
  • Well-scaled — never vanishingly small even when the model is very confidently wrong, which means learning doesn't stall.
  • Linear in the prediction error, so the update size is intuitive.
  • Numerically stable when implemented as a fused "softmax_cross_entropy" op.

MSE on top of softmax outputs is poorly behaved by comparison. If the model is confidently wrong (say it predicts 0.99 for the wrong class), the squared error is small in magnitude, but more importantly the gradient is also squashed by the derivative of the softmax — so the network barely updates, even though it's making a glaring mistake. Cross-entropy avoids that trap entirely: confidently wrong predictions produce large gradients and get corrected quickly.

There are edge cases where MSE for classification makes sense (some calibration settings, certain distillation setups), but for vanilla supervised classification, softmax + cross-entropy is the right default and has been since the late 1980s.`,
      summary: 'Cross-entropy vs MSE.',
      parentIds: ['n3'],
      createdAt: 6,
      isTrunk: false,
    },
    {
      id: 's3',
      prompt: 'What is the chain rule?',
      reply: `The chain rule is the rule of calculus that tells you how to differentiate a composition of functions. If you have a function that is built by feeding the output of one function into another — say h(x) = f(g(x)) — then the derivative is:

       h'(x) = f'(g(x)) · g'(x)

In words: differentiate the outer function, evaluated at the inner function, and multiply by the derivative of the inner function. Intuitively, if a small wiggle in x produces a wiggle in g(x), and that wiggle in g(x) produces a wiggle in f, the total wiggle in the output is the product of the two local sensitivities.

For multivariable functions, the same idea generalizes via the Jacobian. If you have y = f(u) and u = g(x), where everything is vector-valued, then:

       ∂y/∂x = (∂y/∂u) · (∂u/∂x)

— a matrix product of Jacobians. Stacking many such compositions just means multiplying many Jacobians together.

This is exactly what backpropagation exploits. A neural network is a long composition of functions: layer₁ → activation → layer₂ → activation → … → loss. The chain rule says the gradient of the loss with respect to any earlier quantity is the product of the local Jacobians of every operation in between. Backprop computes that product efficiently by walking the computation graph from output to input, multiplying gradients as it goes, and reusing intermediate results so nothing is recomputed.

So when people say "backprop is just the chain rule," they mean it literally — the only cleverness is the bookkeeping that makes the chain-rule product cheap to evaluate over very deep, very wide computation graphs.`,
      summary: 'Chain rule (calculus).',
      parentIds: ['n4'],
      createdAt: 7,
      isTrunk: false,
    },
    {
      id: 'p1',
      prompt: 'What is a gradient?',
      reply: `A gradient is the multivariable generalization of a derivative. For a scalar-valued function f(x₁, x₂, …, xₙ), the gradient is the vector of all its partial derivatives:

       ∇f = [ ∂f/∂x₁,  ∂f/∂x₂,  …,  ∂f/∂xₙ ]

Two key geometric facts make this object central to optimization:
  1. The gradient at a point p points in the direction of steepest increase of f at p.
  2. Its magnitude tells you how steep that increase is — small gradient means the function is nearly flat there, large gradient means it changes rapidly.

That immediately gives you gradient descent: to minimize f, take a small step in the opposite direction of the gradient.

       xₙₑw = xₒₗd − η · ∇f(xₒₗd)

The scalar η is the learning rate (step size). Take steps that are too big and you'll overshoot or oscillate; too small and training will crawl. Modern optimizers (Adam, RMSProp, AdamW, Lion, …) are all variations on this loop that adapt the effective step size per parameter, use running averages to smooth noisy gradients, or decouple weight decay from the gradient update.

A few common points of confusion worth being explicit about:
  • The gradient is defined for scalar-valued functions. For vector-valued functions, the analogous object is the Jacobian (a matrix of partial derivatives).
  • In machine learning the relevant gradient is almost always ∇_θ L, the gradient of the scalar loss L with respect to the parameter vector θ. Even when θ has billions of entries, L is still one number, so ∇_θ L is well-defined.
  • A zero gradient does not necessarily mean you're at a minimum. It could be a maximum, a saddle point, or a flat plateau. In high-dimensional neural-network loss surfaces, saddle points are by far the most common kind of stationary point.`,
      summary: 'Gradient (vector calculus).',
      parentIds: [],
      createdAt: 8,
      isTrunk: false,
    },
  ],
  edges: [
    { from: 'n1', to: 'n2', type: 'subtopic' },
    { from: 'n2', to: 'n3', type: 'subtopic' },
    { from: 'n3', to: 'n4', type: 'subtopic' },
    { from: 'n2', to: 's1', type: 'side-question' },
    { from: 'n3', to: 's2', type: 'side-question' },
    { from: 'n4', to: 's3', type: 'side-question' },
    { from: 'p1', to: 'n4', type: 'prerequisite' },
    { from: 's3', to: 'p1', type: 'see-also' },
  ],
};
