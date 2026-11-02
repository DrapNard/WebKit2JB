# PC validation adapter

The PC laboratory contains WebKitGTK release binaries, Memcheck harnesses, an official crash-regression page, and an x86-64 ASan/ELF education lab. Its official regression page and memory-corruption findings are not part of the Switch portal and are intentionally excluded from this shared client code.

The platform-neutral scripts in `shared/` use classic browser globals, ES5 syntax, a JSON report envelope, capability results, and acknowledged same-origin HTTP POST. They can be loaded by a PC browser test harness, but this task does not alter the PC laboratory or claim that its MiniBrowser exercised these files. Local Node VM tests cover the helper behavior; the Switch server's HTTP integration tests cover routes, provenance, schema rejection, and persistence.
