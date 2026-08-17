export class CorporateError extends Error {
  public constructor(public readonly code: string, public readonly publicMessage: string, options?: ErrorOptions) {
    super(publicMessage, options);
    this.name = "CorporateError";
  }
}
