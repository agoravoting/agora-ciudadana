/*
 * This software incorporates components derived from the
 * Secure Remote Password JavaScript demo developed by
 * Tom Wu (tjw@CS.Stanford.EDU).
 */

// A wrapper for java.math.BigInteger with some appropriate extra functions for JSON and
// generally being a nice JavaScript object.

// why not?
var BigInt = BigInteger;
// ZERO AND ONE are already taken care of
BigInt.TWO = new BigInt("2", 10);

BigInt.setup = function(callback, fail_callback) {
    // nothing to do but go
    callback();
};

BigInt.prototype.toJSONObject = function() {
    return this.toString();
};

BigInt.fromJSONObject = function(s) {
    return new BigInt(s, 10);
};

BigInt.fromInt = function(i) {
    return BigInt.fromJSONObject("" + i);
};

BigInt.use_applet = false;
