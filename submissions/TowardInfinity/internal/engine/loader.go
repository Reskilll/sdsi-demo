package engine

import (
	"encoding/json"
	"fmt"
	"os"
	"strings"
)

// SKU identifies a product. Kept as a plain string; validation ensures it is
// non-empty and free of control characters so it is safe to print and use as a map key.
type SKU string

// Product is one item loaded from inventory.json.
type Product struct {
	SKU        string `json:"sku"`
	Name       string `json:"name"`
	Stock      int    `json:"stock"`
	Limit      int    `json:"userLimit"`  // per-user purchase limit per SKU; must be >= 1
	PricePaise int    `json:"pricePaise"` // exact integer minor units; never floats
}

// Inventory is the parsed inventory.json document.
type Inventory struct {
	Products []Product `json:"products"`
}

// LoadInventory reads and validates an inventory.json file.
func LoadInventory(path string) (*Inventory, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("%w: cannot read %q: %v", ErrInvalidInventory, path, err)
	}
	return ParseInventory(raw)
}

// ParseInventory validates the raw JSON document. Every rejection carries a
// clear message so bad input fails loudly instead of silently misbehaving.
func ParseInventory(raw []byte) (*Inventory, error) {
	var inv Inventory
	dec := json.NewDecoder(strings.NewReader(string(raw)))
	if err := dec.Decode(&inv); err != nil {
		return nil, fmt.Errorf("%w: not valid JSON: %v", ErrInvalidInventory, err)
	}
	if dec.More() {
		return nil, fmt.Errorf("%w: trailing data after JSON object", ErrInvalidInventory)
	}
	if len(inv.Products) == 0 {
		return nil, fmt.Errorf("%w: no products listed", ErrInvalidInventory)
	}
	seen := make(map[string]bool, len(inv.Products))
	for i, p := range inv.Products {
		if strings.TrimSpace(p.SKU) == "" {
			return nil, fmt.Errorf("%w: product %d has empty sku", ErrInvalidInventory, i)
		}
		if seen[p.SKU] {
			return nil, fmt.Errorf("%w: duplicate sku %q", ErrInvalidInventory, p.SKU)
		}
		seen[p.SKU] = true
		if p.Stock < 0 {
			return nil, fmt.Errorf("%w: sku %q has negative stock", ErrInvalidInventory, p.SKU)
		}
		if p.Limit < 1 {
			return nil, fmt.Errorf("%w: sku %q userLimit must be >= 1", ErrInvalidInventory, p.SKU)
		}
		if p.PricePaise < 0 {
			return nil, fmt.Errorf("%w: sku %q has negative price", ErrInvalidInventory, p.SKU)
		}
	}
	return &inv, nil
}
