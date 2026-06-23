/* csim - cosine similarity as a CPython extension.
 *
 * Vectors are received through the buffer protocol as raw arrays of C doubles
 * (pass array.array('d', ...) from Python), so the hot loop runs entirely in
 * native code with no per-element interpreter overhead. That is what makes it
 * fast versus a pure-Python loop.
 */
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <math.h>

static PyObject *csim_cosine(PyObject *self, PyObject *args) {
    Py_buffer a, b;

    /* "y*y*" = two bytes-like objects; array.array('d') qualifies. */
    if (!PyArg_ParseTuple(args, "y*y*", &a, &b))
        return NULL;

    if (a.len != b.len) {
        PyBuffer_Release(&a);
        PyBuffer_Release(&b);
        PyErr_SetString(PyExc_ValueError, "vectors must be the same length");
        return NULL;
    }

    const double *av = (const double *)a.buf;
    const double *bv = (const double *)b.buf;
    Py_ssize_t n = a.len / sizeof(double);

    double dot = 0.0, na = 0.0, nb = 0.0;
    for (Py_ssize_t i = 0; i < n; i++) {
        dot += av[i] * bv[i];
        na  += av[i] * av[i];
        nb  += bv[i] * bv[i];
    }

    PyBuffer_Release(&a);
    PyBuffer_Release(&b);

    if (na == 0.0 || nb == 0.0) {
        PyErr_SetString(PyExc_ValueError, "cosine undefined for a zero vector");
        return NULL;
    }
    return PyFloat_FromDouble(dot / (sqrt(na) * sqrt(nb)));
}

static PyMethodDef CsimMethods[] = {
    {"cosine", csim_cosine, METH_VARARGS,
     "cosine(a, b) -> float. Cosine similarity of two double buffers."},
    {NULL, NULL, 0, NULL}  /* sentinel */
};

static struct PyModuleDef csimmodule = {
    PyModuleDef_HEAD_INIT,
    "csim",                       /* module name */
    "Cosine similarity in C",     /* docstring */
    -1,                           /* per-interpreter state size (-1 = global) */
    CsimMethods
};

PyMODINIT_FUNC PyInit_csim(void) {
    return PyModule_Create(&csimmodule);
}
