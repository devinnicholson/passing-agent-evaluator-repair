Gemma 4 E4B saved-output test-repair replay

This kit separates three questions. Did the required tests execute completely? Did the generated target pass the intended production implementation? Did that target independently detect one declared fault? Complete execution is not semantic adequacy. The kit reproduces saved outputs without regenerating them or changing a model-written body.

Scientific scope

There are five repair units, four historical commits and two seeds per unit. The two Commons Codec units share a commit. Only Jsoup and Codec exercise known selection omissions. Lang and JFreeChart are unaffected-selector controls. Every task was source-exposed. Repeated seeds, paired policies, native repetitions and shared responses do not add independent tasks.

Use kit/PLAN.json and evidence/payload.json for frozen prompts, target identities, provider counts, requirements, faults and seeds. Exact raw records are INITIAL.json, FINAL.json and PARENT_FINAL.json in evidence. A parent collection produced six responses and then timed out. Resumption retained those six unchanged, preserved that timeout as a missing observation and attempted only the three previously unattempted initial slots. PROVENANCE_AUDIT.json records each slot's origin. No scientific outcome was retried to replace an undesirable response.

Training and GPU inference are paused. These E4B outputs use CPU inference and are distinct from the earlier Gemma 4 31B identification predictions. This is a constrained method-body repair pilot, not a main competition harness entry or complete TEBench leaderboard regrade.

Environment

Use disposable Linux amd64 CPU, Python 3.12 and a Java 17 JDK. The native workers used Python 3.12.15, Debian OpenJDK 17.0.20.1 and JUnit Platform 1.11.0. The replay currently expects /usr/lib/jvm/java-17-openjdk-amd64/bin/java and javac. One CPU and one GiB RAM suffice for one method unit at a time. Use fresh absolute output paths. The Linux seccomp filter blocks Internet sockets in native children. It does not replace isolation from credentials or a disposable worker. Do not run untrusted saved programs in a credential-bearing environment.

Setup retrieves hash-pinned Maven artifacts and the released annotation predicate from its pinned TEBench source revision. The upstream predicate is downloaded directly by the reproducer and is excluded from this archive. The function checksum must match the original study before native execution. No cloud account, provider SDK, model access or GPU is needed to replay the saved Java outcomes. Model weights and the Java runtime are not bundled. For exact classfile identity comparisons, use the recorded JDK version. Other Java 17 releases may yield different bytecode despite equal native outcomes.

Preparation from the extracted kit root

  export GEMMA_REPLAY_ROOT="$PWD"
  python3.12 kit/fetch_dependencies.py --output "$GEMMA_REPLAY_ROOT/jars"

Replay the saved initial responses, one unit per fresh output directory

  for unit in jsoup codec_standard codec_url lang jfreechart; do
    python3.12 kit/study.py --units "$unit" --dependencies "$GEMMA_REPLAY_ROOT/jars" --responses "$GEMMA_REPLAY_ROOT/evidence/INITIAL_RESPONSES.json" --output "$GEMMA_REPLAY_ROOT/initial-$unit"
  done

Replay final policy slots

  for unit in jsoup codec_standard codec_url lang jfreechart; do
    python3.12 kit/study.py --units "$unit" --dependencies "$GEMMA_REPLAY_ROOT/jars" --responses "$GEMMA_REPLAY_ROOT/evidence/FINAL_RESPONSES.json" --output "$GEMMA_REPLAY_ROOT/final-$unit"
  done

These final files contain policy slots, not twenty independently generated final responses. The routing table names the exact shared response or retained initial answer behind each slot. Never count the same shared model call twice. Missing responses are explicitly labelled in the normalization and raw records. Their empty transport sentinel is not a fabricated Java patch.

Qualification controls

Run the same command without --responses and with a different fresh output path. Each unit includes developer reference, stale-parent and vacuous targets. All five references must pass developer production and completely fail their declared fault. Vacuous targets must pass both and remain unqualified. Only the generated target contributes to oracle adequacy, so fixed developer controls cannot make an empty target adequate. Assertions use -ea. Every native replay independently checks a deliberately false Java assertion and refuses an assertion-disabled JVM.

Jsoup and Lang faults restore compatible historical production files. JFreeChart restores the historical equals body while preserving new APIs. Codec faults are authored wrong-alphabet substitutions, explicitly distinct from historical production bugs. One-fault adequacy is finite and does not establish exhaustive correctness.

Saved-data analysis and provenance

  python3.12 kit/audit_provenance.py --input "$GEMMA_REPLAY_ROOT/evidence" --output "$GEMMA_REPLAY_ROOT/provenance-replay.json"
  python3.12 kit/analyze_study.py --input "$GEMMA_REPLAY_ROOT/evidence" --output "$GEMMA_REPLAY_ROOT/analysis-replay"

These commands read the scientific archives already included in the kit. They do not execute Java or make model calls. Native reproduction is the separate step above. The audit proves that assertion-enabled initial feedback exactly matches the feedback actually delivered before callback generation, and that resumed response bytes match their retained origin. Provisional assertion-disabled grades remain visible as provisional records, never substituted for the corrected native results.

Post-hoc coverage diagnostic

The frozen scope is exactly the changed production class org.jsoup.nodes.Entities. It compares the exact saved Jsoup 2718 body with its frozen developer-reference body, twice per role in fresh JVMs. It is a single case chosen after observing a weak test. It is not an additional independent task, an estimate of failure prevalence or a full TEBench update score.

  python3.12 kit/fetch_instrumentation.py --output "$GEMMA_REPLAY_ROOT/instrumentation"
  python3.12 kit/coverage_diagnostic.py --units jsoup --dependencies "$GEMMA_REPLAY_ROOT/jars" --responses "$GEMMA_REPLAY_ROOT/evidence/INITIAL_RESPONSES.json" --output "$GEMMA_REPLAY_ROOT/coverage-replay"

Coverage uses JaCoCo 0.8.11 and debug-enabled developer production compiled once for all four roles/repetitions. The ordinary grading study uses -g:none uniformly. The diagnostic binds both roles to the same debug classfile map, class IDs and native class-loading origins. It retains every probe bit and class/method counter. A counterexample is admitted only if all four complete vectors and counters match while the reference detects the historical fault and the model target does not. Equal probe coverage does not imply equal traces, assertion strength or semantics. A nonmatching result must remain negative without changing scope or editing the saved body. The first diagnostic's helper import compilation failure remains preserved as an operational failure before measurement.

Optional inference regeneration

The exact official Google E4B model revision, model SHA256, llama.cpp b11552 runtime artifact and full server arguments are in the raw records. CPU inference uses two threads, no GPU layers, 8192 context, no thinking, temperature 0.7, top-k 40, top-p 0.95 and at most 2048 generated tokens. The request bounds are 550 seconds of native prediction and 600 seconds for the request. Quantization, CPU speed, runtime and these limits constrain observed availability. Template qualification compares the consumed native token IDs, including BOS handling.

  python3.12 kit/export_requests.py --evidence "$GEMMA_REPLAY_ROOT/evidence" --output "$GEMMA_REPLAY_ROOT/recorded-requests"

This exports request JSON without calling a model. After independently setting up the hash-pinned runtime/model, a request may be sent to the loopback /completion endpoint. The JSON contains the exact recorded input token IDs and settings. Generated text can vary across machines even with the same seed. Fresh completions are new data and must never replace saved study observations. The parent timeout has no complete request/response record and is intentionally not exported as a fabricated successful sample.

Interpretation and publication

Report the entire planned denominator, all missing and admission-failed observations, and the number of distinct model calls. Admission failure does not demonstrate semantically incorrect Java. The conservative policy rejects Java Unicode escapes and method-scaffold escapes. Do not claim repaired feedback improved Gemma when the initial feedback contrast never activated. Preserve any null result and the empty compute-matched subset.

The kit contains only scientific source fixtures, public notices, model records, native evidence and replay tools. Provider controllers, credentials, signed transfer URLs, cloud account identities and unrelated project files are excluded. SHA256SUMS binds every distributed file. Preparing this kit does not publish or submit anything. Original private source/result archives remain preserved separately.
