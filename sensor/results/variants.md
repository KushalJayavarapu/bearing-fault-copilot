### Feature variants (seed 42, RF 300 trees, fixed hyperparameters)

| variant | n features | LOLO acc | LOLO macro-F1 | LOLO severity acc | size-out acc (small / medium / large) | size-out acc mean | size-out macro-F1 mean | inner-CV score on loads 0/1/2 |
|---|---|---|---|---|---|---|---|---|
| baseline | 19 | 0.979 | 0.979 | 0.965 | 0.431 / 0.498 / 0.770 | 0.566 | 0.515 | 0.753 |
| +envelope | 28 | 0.990 | 0.989 | 0.977 | 1.000 / 0.497 / 0.715 | 0.737 | 0.675 | 0.836 |
| +envelope -loudness | 25 | 0.989 | 0.988 | 0.956 | 0.996 / 0.517 / 0.721 | 0.745 | 0.685 | 0.835 |

Inner-CV score = mean of inner-LOLO and inner-size-out fault_type macro-F1, computed on training loads only.
Nested LOLO (each outer fold picks its variant by inner CV on its 3 training loads): picks ['+envelope -loudness', '+envelope -loudness', '+envelope', '+envelope'], acc 0.990, macro-F1 0.990.
Selected for the final model (inner CV on loads 0/1/2 only): **+envelope**.
