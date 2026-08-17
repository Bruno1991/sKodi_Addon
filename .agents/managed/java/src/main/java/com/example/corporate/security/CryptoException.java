package com.example.corporate.security;

public final class CryptoException extends RuntimeException {
    private static final long serialVersionUID = 1L;
    private final String code;

    public CryptoException(String code, String message) { super(message); this.code = code; }
    public CryptoException(String code, String message, Throwable cause) { super(message, cause); this.code = code; }
    public String code() { return code; }
}
