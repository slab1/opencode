# Axiom Language Compiler Progress

## LLVM/MLIR Environment Setup
- `llvm-17-dev` installed + `libmlir-17-dev` installed (later swapped for libmlir-18-dev)
- `libmlir-18-dev` installed (required by melior's mlir-sys 0.2.2 which targets LLVM 18)
- `tblgen 0.3.0` (required by melior-macro 0.8.1) needs LLVM 17's TableGen libraries
  - Set `TABLEGEN_17_0_PREFIX=/usr/lib/llvm-17` and `PATH` to include `/usr/lib/llvm-17/bin`
  - `llvm-config-17` must be on PATH before `llvm-config-18` because tblgen checks the default `llvm-config`

## Build Command
```bash
source "$HOME/.cargo/env"
export PATH="/usr/lib/llvm-17/bin:$PATH"
export TABLEGEN_17_0_PREFIX=/usr/lib/llvm-17
export MLIR_DIR=/usr/lib/llvm-18/lib/cmake/mlir
export LLVM_DIR=/usr/lib/llvm-18/lib/cmake/llvm
cargo build -p axiom-compiler --features mlir
```

## Completed Work
- melior 0.14.0, melior-macro 0.8.1, mlir-sys 0.2.2, tblgen 0.3.0 compile successfully
- `emit_mlir.rs`: Implemented `emit_constant_example()` using melior's func::func, arith::constant, func::return
- All 36 tests pass (29 compiler + 7 trace)
- Clean build with 0 warnings

## emit_mlir.rs API Notes
- `func::func(context, name: StringAttribute, type_: TypeAttribute, region: Region, attributes: &[], location)` — 6 args
- `arith::constant(context, value: Attribute, location)` — 3 args (no result type — uses result type inference)
- `func::return(operands, location)` — 2 args
- `IntegerAttribute::new(value: i64, type: Type)` — note arg order: value first, type second
- `IntegerType::new(context, bits: u32)` — then `.into()` to convert to `Type`
- `FunctionType::new(context, inputs: &[Type], outputs: &[Type])`
- `Block::new(&[(Type, Location)])` — takes slice of (type, location) tuples

## Open Issues (9 remaining)
1. #1 — Fork Nova
2. #2 — Wire Nova EXPECT-marker
3. #3 — Add melior (BLOCKED before, now UNBLOCKED ✅)
4. #4 — emit func+arith+scf (DONE: constant example, more needed)
5. #5 — build --backend mlir flag
6. #10 — lower hvm-core
7. #11 — N-body benchmarks
