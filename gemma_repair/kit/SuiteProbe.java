import java.lang.annotation.Annotation;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.*;
import org.junit.platform.engine.TestExecutionResult;
import org.junit.platform.engine.TestSource;
import org.junit.platform.engine.discovery.DiscoverySelectors;
import org.junit.platform.engine.support.descriptor.MethodSource;
import org.junit.platform.launcher.*;
import org.junit.platform.launcher.core.LauncherDiscoveryRequestBuilder;
import org.junit.platform.launcher.core.LauncherFactory;

/** Compiled annotation inventory and native invocation records, not a source parser. */
public final class SuiteProbe {
    private static final Set<String> ANCHORS = new HashSet<>(Arrays.asList(
        "org.junit.jupiter.api.Test", "org.junit.jupiter.api.TestTemplate",
        "org.junit.jupiter.api.RepeatedTest", "org.junit.jupiter.api.TestFactory",
        "org.junit.jupiter.params.ParameterizedTest", "org.junit.Test"));

    private static boolean testAnnotation(Class<? extends Annotation> type, Set<String> seen) {
        if (!seen.add(type.getName())) return false;
        if (ANCHORS.contains(type.getName())) return true;
        for (Annotation annotation : type.getDeclaredAnnotations()) {
            if (testAnnotation(annotation.annotationType(), seen)) return true;
        }
        return false;
    }

    private static String identity(Method method) {
        List<String> params = new ArrayList<>();
        for (Class<?> parameter : method.getParameterTypes()) params.add(parameter.getName());
        return method.getDeclaringClass().getName() + "#" + method.getName()
            + "(" + String.join(",", params) + ")";
    }

    private static String identity(TestIdentifier test) {
        Optional<TestSource> source = test.getSource();
        if (!source.isPresent() || !(source.get() instanceof MethodSource)) return "?";
        MethodSource method = (MethodSource) source.get();
        return method.getClassName() + "#" + method.getMethodName()
            + "(" + method.getMethodParameterTypes().replace(" ", "") + ")";
    }

    private static String encoded(String value) {
        return Base64.getEncoder().encodeToString(value.getBytes(StandardCharsets.UTF_8));
    }

    public static void main(String[] args) throws Exception {
        boolean assertionsEnabled = false;
        assert assertionsEnabled = true;
        if (!assertionsEnabled) throw new IllegalStateException("Java assertions must be enabled with -ea");
        if (args.length < 2) throw new IllegalArgumentException("mode and input required");
        if (args[0].equals("inventory")) {
            List<String> methods = new ArrayList<>();
            for (int index = 1; index < args.length; index++) {
                Class<?> cls = Class.forName(args[index], false, SuiteProbe.class.getClassLoader());
                for (Method method : cls.getDeclaredMethods()) {
                    for (Annotation annotation : method.getDeclaredAnnotations()) {
                        if (testAnnotation(annotation.annotationType(), new HashSet<String>())) {
                            methods.add(identity(method));
                            break;
                        }
                    }
                }
            }
            Collections.sort(methods);
            for (String method : methods) System.out.println("METHOD\t" + method);
            return;
        }
        if (!args[0].equals("execute")) throw new IllegalArgumentException("unknown mode");
        LauncherDiscoveryRequestBuilder builder = LauncherDiscoveryRequestBuilder.request();
        for (String method : Files.readAllLines(Paths.get(args[1]), StandardCharsets.UTF_8)) {
            if (!method.isEmpty()) builder.selectors(DiscoverySelectors.selectMethod(method));
        }
        builder.filters(EngineFilter.includeEngines("junit-jupiter"));
        final int[] failures = new int[] {0};
        Launcher launcher = LauncherFactory.create();
        launcher.registerTestExecutionListeners(new TestExecutionListener() {
            private final Set<String> started = new HashSet<>();
            @Override public void executionStarted(TestIdentifier test) {
                if (test.isTest()) started.add(test.getUniqueId());
            }
            @Override public void executionSkipped(TestIdentifier test, String reason) {
                System.out.println("SKIP\t" + identity(test) + "\t" + encoded(test.getUniqueId())
                    + "\t" + encoded(reason));
            }
            @Override public void executionFinished(TestIdentifier test, TestExecutionResult result) {
                String message = result.getThrowable().map(t -> t.getClass().getName() + ": "
                    + String.valueOf(t.getMessage())).orElse("");
                if (test.isTest()) {
                    if (!started.remove(test.getUniqueId())) throw new IllegalStateException("finish without start");
                    System.out.println("RESULT\t" + identity(test) + "\t" + result.getStatus()
                        + "\t" + encoded(test.getUniqueId()) + "\t" + encoded(message));
                } else if (result.getStatus() != TestExecutionResult.Status.SUCCESSFUL) {
                    System.out.println("CONTAINER\t" + result.getStatus() + "\t" + encoded(message));
                }
                if (result.getStatus() == TestExecutionResult.Status.FAILED) failures[0]++;
            }
        });
        launcher.execute(builder.build());
        System.exit(failures[0] > 0 ? 1 : 0);
    }
}
