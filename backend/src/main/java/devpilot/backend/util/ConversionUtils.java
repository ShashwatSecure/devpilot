package devpilot.backend.util;

/** Shared helpers for coercing loosely-typed values (e.g. parsed JSON/API maps) to Java types. */
public final class ConversionUtils {

    private ConversionUtils() {
    }

    public static Long toLong(Object value) {
        if (value instanceof Number number) {
            return number.longValue();
        }
        return Long.parseLong(String.valueOf(value));
    }

    public static String stringVal(Object value) {
        return value == null ? null : String.valueOf(value);
    }

    public static Integer intVal(Object value) {
        if (value instanceof Number number) {
            return number.intValue();
        }
        if (value == null) {
            return null;
        }
        try {
            return Integer.parseInt(String.valueOf(value));
        } catch (NumberFormatException e) {
            return null;
        }
    }
}
